"""Play the actual published files through the real browser, in both codecs.

The full-sequence pass uses a test-only 16x clock to verify every real ended event.
A separate unaccelerated pass verifies ordinary pause/resume/speed/navigation.
No fake audio, synthetic ended events or production-code changes are used.
"""
import argparse
import asyncio
import json
import shutil
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.async_api import async_playwright

TRACK = r'''({accelerate, mp3}) => {
  window.__audioTrace = {started: [], ended: [], errors: [], objects: []};
  if (mp3) {
    const original = HTMLMediaElement.prototype.canPlayType;
    HTMLMediaElement.prototype.canPlayType = function(type) {
      if (type.includes('opus')) return '';
      return original.call(this, type);
    };
  }
  const RealAudio = window.Audio;
  window.Audio = function(src) {
    const audio = new RealAudio(src);
    window.__audioTrace.objects.push(audio);
    let started = false;
    const play = audio.play.bind(audio);
    audio.play = function() {
      if (!started) { window.__audioTrace.started.push(src); started = true; }
      if (accelerate) audio.playbackRate = 16;
      return play();
    };
    audio.addEventListener('ended', () => window.__audioTrace.ended.push(src));
    audio.addEventListener('error', () => window.__audioTrace.errors.push({src,code:audio.error?.code}));
    return audio;
  };
}'''


async def run(root, report_dir):
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/'
    catalog = json.loads((root / 'content/catalog.json').read_text())
    results = []
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, executable_path=shutil.which('chromium'),
                args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required',
                      '--disable-background-timer-throttling', '--disable-renderer-backgrounding'])
            semaphore = asyncio.Semaphore(3)
            async def full_article(entry, mp3):
                async with semaphore:
                    context = await browser.new_context(viewport={'width': 412, 'height': 915})
                    await context.add_init_script('(' + TRACK + ')(' + json.dumps({'accelerate': True, 'mp3': mp3}) + ')')
                    page = await context.new_page()
                    page_errors = []
                    page.on('pageerror', lambda error: page_errors.append(str(error)))
                    await page.goto(base + '#' + entry['id'])
                    await page.wait_for_selector('.sentence-card')
                    await page.wait_for_function("!document.querySelector('#play-toggle').disabled")
                    doc = json.loads((root / entry['content']).read_text())
                    manifest = json.loads((root / entry['manifest']).read_text())
                    key = 'mp3_path' if mp3 else 'path'
                    expected = [manifest['segments'][s['id']][key] for row in doc['sentences'] for s in row['segments']]
                    await page.locator('#play-toggle').click()
                    await page.wait_for_function("document.querySelector('#player-status').textContent.endsWith('\u2713')", timeout=180000)
                    trace = await page.evaluate('({started:__audioTrace.started,ended:__audioTrace.ended,errors:__audioTrace.errors})')
                    assert trace['started'] == expected, (entry['id'], 'started order', trace)
                    assert trace['ended'] == expected, (entry['id'], 'ended order', trace)
                    assert not trace['errors'] and not page_errors, (trace['errors'], page_errors)
                    assert await page.locator('.sentence-card.is-active').get_attribute('data-index') == str(len(doc['sentences']) - 1)
                    results.append({'article': entry['id'], 'codec': 'mp3' if mp3 else 'opus',
                                    'played_segments': len(expected), 'all_real_ended_events': True})
                    print(json.dumps(results[-1]), flush=True)
                    await context.close()
            await asyncio.gather(*(full_article(entry, mp3) for mp3 in (False, True) for entry in catalog['articles']))
            context = await browser.new_context(viewport={'width': 412, 'height': 915})
            await context.add_init_script('(' + TRACK + ')({accelerate:false,mp3:false})')
            page = await context.new_page()
            await page.goto(base + '#2002-text1')
            await page.wait_for_selector('.sentence-card')
            await page.locator('#play-toggle').click()
            await page.wait_for_function('__audioTrace.objects.some(a=>!a.paused && a.currentTime>0)')
            await page.locator('#play-toggle').click()
            assert await page.evaluate('__audioTrace.objects.every(a=>a.paused)')
            paused = await page.evaluate('__audioTrace.objects.at(-1).currentTime')
            await page.wait_for_timeout(250)
            assert abs(await page.evaluate('__audioTrace.objects.at(-1).currentTime') - paused) < .1
            await page.locator('#play-toggle').click()
            await page.wait_for_function('__audioTrace.objects.some(a=>!a.paused)')
            for rate in (.85, 1, 1.15):
                await page.locator(f'[data-speed="{rate}"]').click()
                assert abs(await page.evaluate('__audioTrace.objects.at(-1).playbackRate') - rate) < .001
            await page.locator('#next').click()
            await page.wait_for_function("document.querySelector('.sentence-card.is-active').dataset.index==='1'")
            await page.evaluate('window.scrollTo(0,0)')
            await page.wait_for_timeout(400)
            await page.locator('#previous').click()
            await page.wait_for_function("document.querySelector('.sentence-card.is-active').dataset.index==='0'")
            await page.evaluate('window.scrollTo(0,0)')
            await page.wait_for_timeout(400)
            await page.locator('#replay').click()
            assert (await page.evaluate('__audioTrace.started.at(-1)')).endswith('/s01-01.opus')
            await page.select_option('#article-select', '2002-translation')
            await page.wait_for_function("document.querySelectorAll('.sentence-card').length===5")
            assert await page.evaluate('__audioTrace.objects.every(a=>a.paused)')
            await page.evaluate('window.scrollTo(0,1000)')
            await page.wait_for_timeout(400)
            assert await page.locator('#player-shell').get_attribute('data-collapsed') == 'true'
            await page.evaluate('window.scrollBy(0,-50)')
            await page.wait_for_timeout(400)
            assert await page.locator('#player-shell').get_attribute('data-collapsed') == 'false'
            report_dir.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(report_dir / '2002-complete-mobile.png'))
            summary = {'real_audio_sequences': results, 'total_played_segments': sum(x['played_segments'] for x in results),
                       'codecs': ['opus', 'mp3'], 'sequence_test_speed': 16,
                       'normal_speed_controls': True, 'pause_resume': True, 'previous_next_replay': True,
                       'selection_stops_previous_audio': True, 'scroll_hide_restore': True,
                       'browser': 'Chromium, mobile viewport; not a physical vivo test',
                       'c_listening_acceptance': 'pending_user_acceptance'}
            (report_dir / '2002-audio-browser.json').write_text(json.dumps(summary, indent=2) + '\n')
            await browser.close()
    finally:
        server.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--report-dir', type=Path, default=Path('reports/browser'))
    args = parser.parse_args()
    asyncio.run(run(args.root, args.report_dir))
