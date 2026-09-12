"""Real-browser reader interaction regression checks; never calls TTS."""
import json
import os
import shutil
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT.parent / 'reports/browser/reader-ux'
REPORT.mkdir(parents=True, exist_ok=True)
BASE = os.getenv('READER_BASE_URL', 'http://127.0.0.1:8766/').rstrip('/') + '/'
server = None
if not os.getenv('READER_BASE_URL'):
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 8766), partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()

class ReaderUX(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = sync_playwright().start()
        cls.browser = cls.p.chromium.launch(headless=True, executable_path=shutil.which('chromium'), args=['--no-sandbox'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.p.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':390,'height':844}, has_touch=True, is_mobile=True)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda e:self.errors.append(str(e)))
        self.page.add_init_script('''(() => { const NativeAudio=window.Audio; window.__audio=[];
          window.Audio=function(...args){ const a=new NativeAudio(...args);window.__audio.push(a);return a; };
          window.Audio.prototype=NativeAudio.prototype;
        })();''')
        self.page.goto(BASE + '?ui=reader-ux#2002-text1')
        self.page.wait_for_selector('.sentence-card')

    def tearDown(self):
        if self.errors:
            self.fail(str(self.errors))
        self.context.close()

    def test_01_hidden_by_default_single_tap_only_opens_its_own_translation(self):
        p=self.page
        self.assertEqual(p.locator('.zh:visible').count(), 0, 'translations must start hidden')
        card=p.locator('.sentence-card').nth(0)
        card.locator('.en').tap()
        self.assertTrue(card.locator('.zh').is_visible())
        self.assertEqual(p.locator('.zh:visible').count(),1)
        self.assertEqual(p.evaluate('window.__audio.filter(a=>!a.paused).length'),0)
        card.locator('.en').tap()
        self.assertFalse(card.locator('.zh').is_visible())
        p.select_option('#article-select','2002-cloze')
        p.wait_for_function("document.querySelectorAll('.sentence-card').length===13")
        self.assertEqual(p.locator('.zh:visible').count(),0)
        p.reload();p.wait_for_selector('.sentence-card')
        self.assertEqual(p.locator('.zh:visible').count(),0)

    def test_02_native_selection_long_press_and_drag_do_not_toggle(self):
        p=self.page
        first=p.locator('.sentence-card').nth(0)
        first.scroll_into_view_if_needed()
        box=first.locator('.en').bounding_box()
        x,y=box['x']+35,box['y']+12
        p.mouse.move(x,y);p.mouse.down();p.wait_for_timeout(650);p.mouse.up()
        self.assertFalse(first.locator('.zh').is_visible())
        p.evaluate('''(() => {const n=document.querySelector('.en .read-token').firstChild;
          const r=document.createRange();r.selectNodeContents(n);getSelection().removeAllRanges();getSelection().addRange(r);
        })()''')
        before=p.evaluate('getSelection().toString()')
        self.assertTrue(before)
        prevented=first.locator('.en').evaluate("el=>!el.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))")
        self.assertFalse(prevented,'native context menu must not be prevented')
        self.assertEqual(p.evaluate('getSelection().toString()'),before)
        first.locator('.en').dispatch_event('click',{'detail':1})
        self.assertFalse(first.locator('.zh').is_visible())
        self.assertEqual(p.evaluate('window.__audio.filter(a=>!a.paused).length'),0)
        p.evaluate('getSelection().removeAllRanges()')
        p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+70,y+20,steps=5);p.mouse.up()
        self.assertFalse(first.locator('.zh').is_visible())
        self.assertEqual(first.locator('.en').evaluate('el=>getComputedStyle(el).userSelect'),'text')

    def test_03_bilingual_highlights_and_single_global_switch(self):
        p=self.page
        self.assertEqual(p.locator('#toggle-chinese,#movie-mode').count(),0)
        self.assertEqual(p.locator('.reader-settings button').count(),1)
        card=p.locator('.sentence-card').nth(1)
        card.locator('.en').tap()
        en=card.locator('.en .vocab').first;zh=card.locator('.zh .zh-vocab').first
        self.assertEqual(en.inner_text().strip(),'sympathy')
        self.assertEqual(zh.inner_text(),'\u8ba4\u540c')
        self.assertGreaterEqual(int(zh.evaluate('el=>getComputedStyle(el).fontWeight')),700)
        p.locator('#toggle-vocab').click()
        self.assertLess(int(en.evaluate('el=>getComputedStyle(el).fontWeight')),700)
        self.assertLess(int(zh.evaluate('el=>getComputedStyle(el).fontWeight')),700)
        self.assertTrue(card.locator('.zh').is_visible())
        p.locator('#toggle-vocab').click()
        self.assertGreaterEqual(int(zh.evaluate('el=>getComputedStyle(el).fontWeight')),700)
        p.screenshot(path=str(REPORT/'bilingual-mobile.png'),full_page=True)

    def test_04_magnetic_slider_and_real_audio_do_not_restart(self):
        p=self.page
        p.locator('#play-toggle').click()
        p.wait_for_function('window.__audio.some(a=>!a.paused&&a.currentTime>.2)',timeout=15000)
        p.evaluate('window.__active=window.__audio.find(a=>!a.paused);window.__before=window.__active.currentTime')
        slider=p.locator('#speed-range')
        slider.focus();slider.press('End')
        self.assertEqual(p.evaluate('window.__active.playbackRate'),2)
        self.assertEqual(p.locator('#speed-value').inner_text(),'2.0\u00d7')
        slider.press('Home')
        self.assertEqual(p.evaluate('window.__active.playbackRate'),.7)
        for expected in [1,1.25,1.5,2]:
            slider.press('ArrowRight')
            self.assertEqual(p.evaluate('window.__active.playbackRate'),expected)
        self.assertGreaterEqual(p.evaluate('window.__active.currentTime'),p.evaluate('window.__before'))
        self.assertEqual(p.locator('.zh:visible').count(),0)
        p.locator('#play-toggle').click()
        p.wait_for_timeout(150)
        self.assertTrue(p.evaluate('window.__active.paused'))
        self.assertGreater(p.locator('.en .is-read').count(),0)
        # Hold, drag and release: the value grows while held, then snaps.
        b=slider.bounding_box();p.mouse.move(b['x']+b['width']*.39,b['y']+b['height']/2);p.mouse.down()
        self.assertTrue(p.locator('#speed-control').evaluate("el=>el.classList.contains('is-dragging')"))
        p.screenshot(path=str(REPORT/'speed-drag-mobile.png'),full_page=False)
        p.mouse.move(b['x']+b['width']*.56,b['y']+b['height']/2,steps=8);p.mouse.up()
        self.assertIn(p.evaluate('window.__active.playbackRate'),[.7,1,1.25,1.5,2])
        self.assertFalse(p.locator('#speed-control').evaluate("el=>el.classList.contains('is-dragging')"))

    def test_05_sentence_play_is_separate_and_translation_stays_hidden(self):
        p=self.page
        p.locator('.sentence-play').nth(1).click()
        p.wait_for_function('window.__audio.some(a=>!a.paused&&a.currentTime>.1)',timeout=15000)
        self.assertEqual(p.locator('.zh:visible').count(),0)
        self.assertTrue(p.locator('#player-position').inner_text().startswith('02'))
        p.locator('#replay').click()
        self.assertTrue(p.locator('#player-position').inner_text().startswith('02'))
        p.locator('#next').click()
        self.assertTrue(p.locator('#player-position').inner_text().startswith('03'))
        p.locator('#previous').click()
        self.assertTrue(p.locator('#player-position').inner_text().startswith('02'))

    def test_06_all_articles_text_unchanged_and_hidden(self):
        p=self.page
        for article in ['cloze','text1','text2','text3','text4','translation']:
            doc=json.loads((ROOT/f'content/2002/c/{article}.json').read_text())
            p.select_option('#article-select','2002-'+article)
            p.wait_for_function('(txt)=>document.querySelector(".en")?.textContent===txt',arg=doc['sentences'][0]['en'])
            actual=p.locator('.sentence-card').evaluate_all('cs=>cs.map(c=>({en:c.querySelector(".en").textContent,zh:c.querySelector(".zh").textContent}))')
            self.assertEqual(actual,[{'en':s['en'],'zh':s['zh']} for s in doc['sentences']])
            self.assertEqual(p.locator('.zh:visible').count(),0)

    def test_07_scroll_hide_restore_and_no_mobile_overflow(self):
        p=self.page
        p.evaluate('window.scrollTo(0,1300)');p.wait_for_timeout(450)
        self.assertEqual(p.locator('#player-shell').get_attribute('data-collapsed'),'true')
        p.evaluate('window.scrollBy(0,-70)');p.wait_for_timeout(450)
        self.assertEqual(p.locator('#player-shell').get_attribute('data-collapsed'),'false')
        self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),p.evaluate('window.innerWidth'))
        p.screenshot(path=str(REPORT/'english-only-mobile.png'),full_page=False)

if __name__=='__main__':
    try:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReaderUX))
        (REPORT/'result.json').write_text(json.dumps({'base_url':BASE,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()},indent=2))
    finally:
        if server:server.shutdown()
    raise SystemExit(0 if result.wasSuccessful() else 1)
