"""Archive the prior interpretation and withdraw invalid default-profile inferences."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent
now=datetime.now(timezone.utc)
note_path=ROOT/'interpretation_correction.json'
if note_path.exists():
    raise RuntimeError('Correction already exists; do not create duplicate history.')
old=json.loads((ROOT/'results.json').read_text(encoding='utf-8'))
archive=ROOT/'interpretation_archive'/now.strftime('%Y%m%dT%H%M%SZ')
archive.mkdir(parents=True)
names=set(old['artifact_sha256'])|{'report.html','results.json','build_report.py','render_report.py','qa/report-desktop.png'}
copied={}
for name in sorted(names):
    source=ROOT/name
    if not source.is_file(): continue
    target=archive/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
    copied[name]=digest
(archive/'archive_manifest.json').write_text(json.dumps({'copied_at_utc':now.isoformat(),'sha256':copied},ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
note={
 'corrected_at_utc':now.isoformat(),
 'user_correction_verbatim':'你只给那么点时间肯定完不成参数啊，如果你想控制的话应该显式调用函数头才对嘛',
 'archive_relative':archive.relative_to(ROOT).as_posix(),
 'status':'Prior inferences about default DIGR investment design and full-run efficiency are withdrawn.',
 'confirmed_design_errors':[
  'b05 retained default N12/R4/D3/V3 but separately imposed 900 seconds including U0, at most three helper identities and six helper turns; adequacy for completing those responsibilities was not established.',
  'Protocol text was injected into a simulated task rather than using an actual explicit DIGR(...) invocation declaring a controlled configuration.',
  'Parameter shortfalls after this externally imposed cutoff were used to question default depth and minimum counts; that inference is unsupported.',
  'The observed cost of a truncated trajectory was compared with completed native runs; it is not the cost of completing the default protocol.',
  'An external all-in wall limit was conflated with protocol timing; formal T/t, preliminary work and exclusive D/V work have distinct scopes in this pinned profile.'
 ],
 'withdrawn_judgments':[
  '当前默认深执行配置偏重',
  '本次实验支持怀疑刚性的最低次数',
  '未完成默认参数或超出研究者外部900秒限制构成DIGR本身的负面表现证据',
  '该模拟组的观测成本足以评价完整默认DIGR的投入产出'
 ],
 'retained_observations':[
  'All four functional artifacts passed the frozen acceptance checks in each accepted episode.',
  'A bounded-state budget implementation was actually adopted and has a measured auxiliary-allocation benefit on the declared exploratory synthetic workloads.',
  'Recorded wall time and token counters describe observed trajectories; they are not complete-default cost estimates.',
  'The extra starter Python cache is a task-scope violation independent of the parameter/cutoff error; original input bytes were unchanged.'
 ],
 'valid_future_comparison_requirements':[
  'For default-profile efficacy, invoke the actual default profile and allow its complete responsibilities to finish before comparing outcome and total resource use.',
  'For a controlled configuration, declare the N/T/R/S/D/V/L/M choices in the function header before execution, run that declared configuration to completion, and freeze the control beforehand.',
  'In pinned 0.7.0 target=15min is a soft target and min=15min requests a lower bound; neither is an upper cutoff. A real external stop creates a censored observation.',
  'Do not backfill a function header with the already observed N6/R2/D1/V3 and relabel the old run as completed.'
 ],
 'rerun_performed_in_this_correction':False,
 'raw_data_mutated':False
}
note_path.write_text(json.dumps(note,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
fidelity=json.loads((ROOT/'fidelity.json').read_text(encoding='utf-8'))
fidelity['user_facing_conclusion']='原实验没有正确检验默认DIGR：保留默认目标，却在函数头外另加时限与代理配额；参数未完成不能据此归咎于协议。撤回“默认深执行偏重”和对最低次数的负面判断。局部代码改进与原始观测保留。'
fidelity['default_profile_efficacy_evaluable']=False
fidelity['parameter_shortfall_is_negative_efficacy_evidence']=False
fidelity['controlled_function_header_invoked']=False
fidelity['observation_censored_by_experimenter_design']=True
fidelity['correction_record']='interpretation_correction.json'
fidelity['findings']=[
 '设计错误：保留N12/R4/D3/V3，却另加900秒、三个helper身份和六次helper turn的外部限制；未先用显式函数头声明适配的受控配置。',
 '原来的“默认配置偏重、最低次数值得怀疑”判断撤回。N6/R2/D1/V3只描述被外部截断时的自报停点，不是默认协议负担或效果的证据。',
 '932.604秒及token仍是这段模拟运行的观测值，不能标为完成默认配置所需资源；超过研究者的900秒不能算违反协议T/t。',
 '独立研究与预算索引改进有实际材料、采用记录和性能探针支持；该局部事实保留，但不构成完整默认DIGR的对照结论。',
 '新增1662字节starter缓存违反写入边界，原件字节未改。该事实独立保留，不扩大为默认配置负面结论。'
]
(ROOT/'fidelity.json').write_text(json.dumps(fidelity,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
(ROOT/'build_report.py').write_text('"""Current corrected-report entry; prior generator is archived."""\nfrom build_corrected_report import build\n\nif __name__ == "__main__":\n    build()\n',encoding='utf-8',newline='\n')
for name,digest in copied.items():
    if name in ('report.html','results.json','build_report.py','fidelity.json'): continue
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,(name,'original data changed')
print(json.dumps({'archived_files':len(copied),'archive':str(archive),'raw_records_unchanged':True},ensure_ascii=False))
