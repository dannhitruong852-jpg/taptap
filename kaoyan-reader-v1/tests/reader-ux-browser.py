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
AUDIO_VERSION = os.getenv('READER_AUDIO_VERSION', '').strip()

def reader_url(ui='reader-ux'):
    version = f'&audioVersion={AUDIO_VERSION}' if AUDIO_VERSION else ''
    return BASE + f'?ui={ui}{version}#2002-text1'
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
        cls.browser.close();cls.p.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':390,'height':844}, has_touch=True, is_mobile=True)
        self.page = self.context.new_page();self.errors = []
        self.page.on('pageerror', lambda e:self.errors.append(str(e)))
        self.page.add_init_script('''(() => { const NativeAudio=window.Audio; window.__audio=[];
          window.Audio=function(...args){ const a=new NativeAudio(...args); a.__playCalls=0;
            const nativePlay=a.play.bind(a); a.play=(...playArgs)=>{a.__playCalls++;return nativePlay(...playArgs);};
            window.__audio.push(a);return a; };
          window.Audio.prototype=NativeAudio.prototype;
          try{Object.defineProperty(window,'AudioContext',{value:undefined,configurable:true});}catch(e){}
          try{Object.defineProperty(window,'webkitAudioContext',{value:undefined,configurable:true});}catch(e){}
        })();''')
        self.page.goto(reader_url());self.page.wait_for_selector('.sentence-card')

    def tearDown(self):
        if self.errors:self.fail(str(self.errors))
        self.context.close()

    def test_01_hidden_by_default_single_tap_only_opens_its_own_translation(self):
        p=self.page;self.assertEqual(p.locator('.zh:visible').count(),0)
        card=p.locator('.sentence-card').nth(0);card.locator('.en').tap();p.wait_for_timeout(340);self.assertTrue(card.locator('.zh').is_visible());self.assertEqual(p.locator('.zh:visible').count(),1)
        self.assertEqual(sum(p.evaluate('window.__audio.map(a=>a.__playCalls)')),0);p.wait_for_timeout(600);card.locator('.en').tap();p.wait_for_timeout(340);self.assertFalse(card.locator('.zh').is_visible())
        p.select_option('#article-select','2002-cloze');p.wait_for_function("document.querySelectorAll('.sentence-card').length===13");self.assertEqual(p.locator('.zh:visible').count(),0)
        p.reload();p.wait_for_selector('.sentence-card');self.assertEqual(p.locator('.zh:visible').count(),0)

    def test_02_native_selection_long_press_and_drag_do_not_toggle_or_play(self):
        p=self.page;first=p.locator('.sentence-card').nth(0);en=first.locator('.en');en.evaluate("el=>el.scrollIntoView({block:'center',behavior:'instant'})");p.wait_for_timeout(100)
        box=en.bounding_box();x,y=box['x']+35,box['y']+12
        self.assertTrue(en.evaluate("(el,p)=>{const hit=document.elementFromPoint(p.x,p.y);return !!hit&&(hit===el||el.contains(hit));}",{'x':x,'y':y}))
        p.mouse.move(x,y);p.mouse.down();p.wait_for_timeout(650);p.mouse.up();self.assertFalse(first.locator('.zh').is_visible());self.assertEqual(sum(p.evaluate('window.__audio.map(a=>a.__playCalls)')),0)
        p.evaluate('''(() => {const n=document.querySelector('.en .read-token').firstChild;const r=document.createRange();r.selectNodeContents(n);getSelection().removeAllRanges();getSelection().addRange(r);})()''')
        before=p.evaluate('getSelection().toString()');self.assertTrue(before);prevented=en.evaluate("el=>!el.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}))");self.assertFalse(prevented);self.assertEqual(p.evaluate('getSelection().toString()'),before)
        en.dispatch_event('click',{'detail':1});self.assertFalse(first.locator('.zh').is_visible());p.evaluate('getSelection().removeAllRanges()')
        p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+70,y+20,steps=5);p.mouse.up();self.assertFalse(first.locator('.zh').is_visible());self.assertEqual(en.evaluate('el=>getComputedStyle(el).userSelect'),'text')

    def test_03_bilingual_highlights_and_single_global_switch(self):
        p=self.page;self.assertEqual(p.locator('#toggle-chinese,#movie-mode').count(),0);self.assertEqual(p.locator('.reader-settings button').count(),2);self.assertEqual(p.locator('#phrase-book-open').count(),1)
        card=p.locator('.sentence-card').nth(1);card.locator('.en').tap();en=card.locator('.en .vocab').first;zh=card.locator('.zh .zh-vocab').first
        self.assertEqual(en.inner_text().strip(),'sympathy');self.assertEqual(zh.inner_text(),'认同');self.assertGreaterEqual(int(zh.evaluate('el=>getComputedStyle(el).fontWeight')),700)
        p.locator('#toggle-vocab').click();self.assertLess(int(en.evaluate('el=>getComputedStyle(el).fontWeight')),700);self.assertTrue(card.locator('.zh').is_visible());p.locator('#toggle-vocab').click();self.assertGreaterEqual(int(zh.evaluate('el=>getComputedStyle(el).fontWeight')),700)


    def test_03b_phrase_selection_uses_bottom_bar_and_year_book(self):
        p=self.page
        card=p.locator('.sentence-card').nth(1)
        token=card.locator('.en .vocab').first
        self.assertEqual(token.inner_text().strip(),'sympathy')
        p.evaluate("""(() => {
          const node=document.querySelectorAll('.sentence-card')[1].querySelector('.en .vocab').firstChild;
          const range=document.createRange();range.selectNodeContents(node);
          const selection=getSelection();selection.removeAllRanges();selection.addRange(range);
        })()""")
        p.wait_for_selector('#phrase-study-bar:not([hidden])')
        self.assertEqual(p.locator('#phrase-highlight-selection').inner_text().strip(),'sympathy')
        bar=p.locator('#phrase-study-bar').bounding_box()
        player=p.locator('#player-shell').bounding_box()
        self.assertLessEqual(bar['y']+bar['height'],player['y']+1)
        p.locator('#phrase-highlight-action').click()
        p.wait_for_timeout(120)
        self.assertEqual(card.locator('.en .phrase-mark-en').count(),1)
        card.locator('.en').tap();p.wait_for_timeout(340);self.assertTrue(card.locator('.zh').is_visible())
        self.assertGreaterEqual(card.locator('.zh .phrase-mark-zh').count(),1)
        self.assertIn('2002 词群本',p.locator('#phrase-book-open').inner_text())
        p.locator('#phrase-book-open').click();self.assertTrue(p.locator('#phrase-book-backdrop').is_visible())
        self.assertEqual(p.locator('#phrase-book-year').input_value(),'2002')
        self.assertEqual(p.locator('.phrase-book-item').count(),1)
        self.assertEqual(p.locator('.phrase-book-en').inner_text().strip(),'sympathy')
        self.assertTrue(p.locator('.phrase-book-zh').inner_text().strip())
        p.locator('#phrase-book-blur').click()
        self.assertEqual(p.locator('#phrase-book-blur').get_attribute('aria-pressed'),'true')
        self.assertTrue(p.locator('.phrase-book-panel').evaluate("el=>el.classList.contains('is-blurred')"))

    def test_04_four_option_speed_menu_changes_live_audio_without_restart(self):
        p=self.page;p.locator('#play-toggle').click();p.wait_for_function('window.__audio.some(a=>!a.paused&&a.currentTime>.2)',timeout=15000)
        p.evaluate('window.__active=window.__audio.find(a=>!a.paused);window.__before=window.__active.currentTime')
        trigger=p.locator('#speed-value');trigger.click();self.assertTrue(p.locator('.speed-menu').is_visible());self.assertEqual(p.locator('.speed-menu [data-speed]').count(),4)
        p.locator('.speed-menu [data-speed="1.7"]').click();self.assertEqual(p.evaluate('window.__active.playbackRate'),1.7);self.assertEqual(trigger.inner_text(),'1.7×');self.assertFalse(p.locator('.speed-menu').is_visible())
        self.assertGreaterEqual(p.evaluate('window.__active.currentTime'),p.evaluate('window.__before'))
        trigger.click();p.locator('.speed-menu [data-speed="0.7"]').click();self.assertEqual(p.evaluate('window.__active.playbackRate'),.7);self.assertEqual(trigger.inner_text(),'0.7×')
        p.locator('#play-toggle').click();p.wait_for_timeout(150);self.assertTrue(p.evaluate('window.__active.paused'))
        p.screenshot(path=str(REPORT/'x-player-speed-menu.png'),full_page=False)

    def test_05_player_previous_next_controls_switch_whole_articles_not_sentences(self):
        p=self.page;p.locator('.sentence-play').nth(1).click();p.wait_for_function('window.__audio.some(a=>!a.paused&&a.currentTime>.1)',timeout=15000)
        self.assertTrue(p.locator('#player-position').inner_text().startswith('02'))
        p.locator('#next').click()
        p.wait_for_function("document.querySelector('#article-select').value==='2002-text2' && document.querySelector('#player-position').textContent.trim().startsWith('01') && document.querySelectorAll('.sentence-card').length===16")
        self.assertEqual(p.locator('#article-select').input_value(),'2002-text2');self.assertTrue(p.locator('#player-position').inner_text().startswith('01'))
        p.locator('#previous').click()
        p.wait_for_function("document.querySelector('#article-select').value==='2002-text1' && document.querySelector('#player-position').textContent.trim().startsWith('01') && document.querySelectorAll('.sentence-card').length===21")
        self.assertEqual(p.locator('#article-select').input_value(),'2002-text1')
        self.assertEqual(p.locator('#replay').count(),0)

    def test_06_all_articles_text_unchanged_and_hidden(self):
        p=self.page
        for article in ['cloze','text1','text2','text3','text4','translation']:
            doc=json.loads((ROOT/f'content/2002/c/{article}.json').read_text());p.select_option('#article-select','2002-'+article);p.wait_for_function('(txt)=>document.querySelector(".en")?.textContent===txt',arg=doc['sentences'][0]['en'])
            actual=p.locator('.sentence-card').evaluate_all('cs=>cs.map(c=>({en:c.querySelector(".en").textContent,zh:c.querySelector(".zh").textContent}))');self.assertEqual(actual,[{'en':s['en'],'zh':s['zh']} for s in doc['sentences']]);self.assertEqual(p.locator('.zh:visible').count(),0)

    def test_07_scroll_hide_restore_and_no_mobile_overflow(self):
        p=self.page;p.evaluate('window.scrollTo(0,1300)');p.wait_for_timeout(500);self.assertEqual(p.locator('#player-shell').get_attribute('data-collapsed'),'true')
        p.evaluate('window.scrollBy(0,-70)');p.wait_for_timeout(500);self.assertEqual(p.locator('#player-shell').get_attribute('data-collapsed'),'false');self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),p.evaluate('window.innerWidth'))

    def test_08_approved_x_style_player_geometry_and_upward_speed_menu(self):
        p=self.page;shell=p.locator('#player-shell').bounding_box();self.assertAlmostEqual(shell['width'],390,delta=1.5);self.assertAlmostEqual(shell['y']+shell['height'],844,delta=1.5);self.assertGreaterEqual(shell['height'],75);self.assertLessEqual(shell['height'],78)
        selectors=['#previous','#play-toggle','#next','#speed-value'];expected=[(46,46),(56,56),(46,46),(68,38)]
        boxes=[]
        for selector,size in zip(selectors,expected):
            box=p.locator(selector).bounding_box();boxes.append(box);self.assertEqual((round(box['width']),round(box['height'])),size)
        centers=[b['x']+b['width']/2 for b in boxes];self.assertEqual(centers,sorted(centers));self.assertLessEqual(boxes[-1]['x']+boxes[-1]['width'],390)
        p.locator('#speed-value').click();menu=p.locator('.speed-menu').bounding_box();self.assertLess(menu['y'],boxes[-1]['y']);self.assertEqual(p.locator('.speed-menu [data-speed]').all_inner_texts(),['1.7×','1.3×','1.0×','0.7×'])
        p.screenshot(path=str(REPORT/'x-player-mobile.png'),full_page=False)

    def test_09_real_timestamp_index_and_three_mobile_widths(self):
        p=self.page
        script="""async()=>{const m=await import('./time-index.js');const words=[{start:0,end:4},{start:4,end:4.5},{start:4.5,end:5},{start:5,end:5.5},{start:5.5,end:6},{start:6,end:6.8},{start:6.8,end:7.5},{start:7.5,end:8.2},{start:8.2,end:9},{start:9,end:10}];return [m.activeWordIndex(words,3),m.activeWordIndex(words,5.25),m.readStateAtTime(words,3)];}"""
        result=p.evaluate(script);self.assertEqual(result[0],0);self.assertEqual(result[1],3);self.assertEqual(result[2],{'readThrough':0,'active':0})
        for width,height in [(320,700),(390,844),(412,915)]:
            context=self.browser.new_context(viewport={'width':width,'height':height},has_touch=True,is_mobile=True)
            try:
                page=context.new_page();page.goto(reader_url('x-player-size'));page.wait_for_selector('#player-shell');shell=page.locator('#player-shell').bounding_box();self.assertAlmostEqual(shell['width'],width,delta=1.5);self.assertAlmostEqual(shell['y']+shell['height'],height,delta=1.5);self.assertGreaterEqual(shell['height'],75);self.assertLessEqual(shell['height'],78);self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),width)
                expected=[42,52,42,62] if width<=350 else [46,56,46,68]
                for selector,side in zip(['#previous','#play-toggle','#next','#speed-value'],expected):self.assertAlmostEqual(page.locator(selector).bounding_box()['width'],side,delta=.6)
            finally:context.close()

if __name__=='__main__':
    try:
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReaderUX));(REPORT/'result.json').write_text(json.dumps({'base_url':BASE,'audio_version':AUDIO_VERSION,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()},indent=2))
    finally:
        if server:server.shutdown()
    raise SystemExit(0 if result.wasSuccessful() else 1)
