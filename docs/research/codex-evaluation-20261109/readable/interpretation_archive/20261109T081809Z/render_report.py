import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent
QA=ROOT/'qa'
QA.mkdir(exist_ok=True)
chrome=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
assert chrome.is_file()
cmd=[str(chrome),'--headless=new','--disable-gpu','--disable-background-networking',
     '--disable-component-update','--no-first-run','--no-default-browser-check',
     '--user-data-dir='+str(QA/'browser-profile'),'--window-size=1280,1700',
     '--screenshot='+str(QA/'report-desktop.png'),'--dump-dom',(ROOT/'report.html').as_uri()]
p=subprocess.run(cmd,encoding='utf-8',text=True,capture_output=True,timeout=60,
                 creationflags=subprocess.CREATE_NO_WINDOW)
(QA/'rendered.html').write_text(p.stdout,encoding='utf-8')
(QA/'browser-stderr.txt').write_text(p.stderr,encoding='utf-8')
print(json.dumps({'exit_code':p.returncode,'screenshot_exists':(QA/'report-desktop.png').is_file(),
 'rendered_contains_conclusion':'这轮发现了真实的局部代码改进' in p.stdout,
 'rendered_contains_scope_failure':'1662' in p.stdout,
 'rendered_contains_memory_result':'1344.9' in p.stdout,
 'browser_profile_real_location':str((QA/'browser-profile').resolve())},ensure_ascii=False))
