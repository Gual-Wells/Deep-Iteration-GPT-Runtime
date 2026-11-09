from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent
VISIBILITY='''盲法边界补充（所有后续被试及其helper同样适用）：不得调用collaboration.list_agents或全局thread列表，不查看父级完整对话/其他任务摘要，不读取任何其他被试。全局列表会暴露已完成被试的答案。只能用自己实际spawn返回的身份及send_message/followup/wait进行本线管理。若意外收到别线答案，立即只向父级报告并停止依赖该信息的生产；不能声称“已忘记”而恢复盲法。请将此边界逐字传给本线每个helper。\n'''
plan=json.loads((ROOT/'native_plan.json').read_text(encoding='utf-8'))
old=next(r for r in plan['records'] if r['label']=='b02')
new=dict(old,label='b05',workspace=str(ROOT/'native_subjects/b05'),prompt_file=str(ROOT/'native_prompts/b05.txt'))
newdest=Path(new['workspace'])
newdest.mkdir()
shutil.copytree(ROOT/'frozen_seed',newdest/'portfolio')
(newdest/'run').mkdir()
prompt=VISIBILITY+Path(old['prompt_file']).read_text(encoding='utf-8').replace(old['workspace'],new['workspace'])
Path(new['prompt_file']).write_text(prompt,encoding='utf-8')
new['prompt_sha256']=hashlib.sha256(prompt.encode()).hexdigest()
plan['excluded_records']=[dict(old,excluded_reason='Preproduction context contamination via global list_agents showing baseline final answer; interrupted without simulated execution confirmation.')]
plan['records']=[new if r['label']=='b02' else r for r in plan['records']]
for record in plan['records']:
    if record['label'] not in ('b03','b04'): continue
    path=Path(record['prompt_file']); text=VISIBILITY+path.read_text(encoding='utf-8')
    path.write_text(text,encoding='utf-8'); record['prompt_sha256']=hashlib.sha256(text.encode()).hexdigest()
plan['visibility_repair']={'at_utc':datetime.now(timezone.utc).isoformat(),'reason':'Global list_agents exposes completed sibling answers even when histories are fork_none.','changes':'Explicitly enforce the already-declared no-other-subjects boundary for future parents/helpers. No task inputs, evaluator, acceptance rules or outcome targets changed.'}
(ROOT/'native_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
p=ROOT/'preregistration.json'; data=json.loads(p.read_text(encoding='utf-8'))
data['visibility_repair_before_full_production']=plan['visibility_repair']; data['excluded_native_runs']=plan['excluded_records']; data['actual_native_plan']=plan['records']
p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
report=ROOT/'build_report.py'; text=report.read_text(encoding='utf-8')
text=text.replace("LABELS = ['b01', 'b02', 'b03', 'b04']", "LABELS = ['b01', 'b05', 'b03', 'b04']").replace("'b02': '完整", "'b05': '完整").replace("r['label']=='b02'", "r['label']=='b05'").replace('score.py b01 b02 b03 b04','score.py b01 b05 b03 b04')
report.write_text(text,encoding='utf-8')
print(json.dumps({'new_full_label':'b05','prompt_file':new['prompt_file'],'baseline_b01_not_altered':True},ensure_ascii=False))
