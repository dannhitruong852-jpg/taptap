import json
import threading
import shutil
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
(root.parent/'reports/browser').mkdir(parents=True,exist_ok=True)
server=ThreadingHTTPServer(('127.0.0.1',8765),partial(SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':412,'height':915},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8765')
    page.wait_for_selector('.sentence-card')
    assert page.locator('.sentence-card').count()==21
    page.screenshot(path=str(root.parent/'reports/browser/mobile-2002.png'),full_page=False)
    page.select_option('#article-select','2002-cloze');page.wait_for_timeout(200)
    assert page.locator('.sentence-card').count()==13
    page.select_option('#section-select','translation');page.wait_for_timeout(200)
    assert page.locator('.sentence-card').count()==5
    assert page.locator('#article-select option').count()==1
    page.select_option('#section-select','reading');page.wait_for_timeout(200)
    assert page.locator('#article-select option').count()==4
    assert page.locator('.sentence-card').count()==21
    page.evaluate('window.scrollTo(0,1300)');page.wait_for_timeout(350)
    assert page.locator('#player-shell').get_attribute('data-collapsed')=='true'
    page.evaluate('window.scrollBy(0,-50)');page.wait_for_timeout(350)
    assert page.locator('#player-shell').get_attribute('data-collapsed')=='false'
    page.screenshot(path=str(root.parent/'reports/browser/mobile-reader.png'),full_page=False)
    assert not errors,errors
    print(json.dumps({'mobile_layout':True,'six_article_navigation':True,'scroll_hide_restore':True,'page_errors':errors}))
    browser.close()
server.shutdown()
