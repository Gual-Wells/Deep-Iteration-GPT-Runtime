from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
COMMON = '''用户已明确授权这项隔离试验及任务内独立分工。你的当前任务是完成这个固定portfolio的四件实际产物，原件、质量要求、目录和允许修改范围都在portfolio/TASK.txt及四个子目录TASK.txt中。
只读取你自己的试验目录及其Git历史；不读其他被试、support/、评分器、gold、用户其他项目或历史。题目完全自含，不需要网络、真实招聘信息、外部服务、模型API或依赖安装。不调用另一个Codex CLI。
只可在portfolio各任务output/中生成交付物；可在自己的run/中保存必要的简短公开工作记录，不保存隐藏思维链。不得改输入、starter/、TASK、history当前树或HEAD。Python调用加-B以避免写入输入缓存。
你的历史是全新的，但宿主仍注入相同的全局AGENTS，其中有普通轻量约定；它是本实验的共同背景。只按本条明确指定的处理条件执行，不能去研究别的处理条件或评价哪个条件应赢。
最终给实际产物位置、实际检查和未完成事项。不要为用满预算而添加无用工作。所有模型、工具与协作资源都记录为实际开销，不从角色数、文字或标签推定质量。
'''
RESOURCE = '''资源上限：从本次Main启动起总墙钟900秒，最多3个独立helper身份、最多2个helper同时活跃、helper初始及follow-up合计最多6个turn。必须fork_turns=none，helper只拿必要受控材料，所有child遵守相同目录边界。允许自主决定如何使用这些资源，当前任务授权包含真实独立分工，不需要另请权限。子代理不得再扩张身份/turn总额。Main对完整交付负责。
这是假设相同分配上限，不代表相同实际token。若上限内不能完整完成，保留真实未完成状态，不能伪造完成。
'''
FULL = '''处理条件：在本轮实验中执行已冻结的DIGR Codex 0.7.0完整profile，P_run=0.7.0@b258276632054f7f8d1d8a060e01b98b9c7aa3be。这里是实验操作者调用的脚本模拟任务，不是主会话用户新的真实DIGR业务调用。父级已在本轮通过GitHub connector实际取得此branch HEAD及同SHA原文并验证manifest/VERSION；你应读已冻结的pin/codex/manifest.json、VERSION、STARTUP及entrypoint全部core（FOUNDATION、CHARACTER、PARAMETERS、COLLABORATION、PERMISSIONS），只能以这些实际字节作处理条件。可读pin/provenance.json核对；不临时更换pin、联网追新或读取根stable。传输层不在本任务估计内。
默认正式责任保留N12/R4/D3/V3/L3/M1；T/t按任务形成有依据的软目标，不强加无用等待，资源上限仍优先。正文的研究、生产、协作、公开记录责任均由你承担。N/R只认实质问题与完整候选重开，V需初研形成领域且相关候选后同线再入，D需真实强替代及Main处理，不用同一返回自动双标充数。任何不足都如实报告，不自主降档以冒称完整执行。
先做有材料依据的U0说明并将会改变路线的待决问题发给父级。父级将作为实验操作者给出明确标识的模拟用户决定；该决定仅针对这套冻结四任务与资源上限，不是伪造真实用户确认。收到后才全面生产。前置成本与正式成本分别说明，最终all-in成本都纳入试验。
'''

records = [
    {'label':'b01', 'condition':'host_native_single', 'repeat':1, 'cap':480},
    {'label':'b02', 'condition':'full_profile_default_capped', 'repeat':1, 'cap':900},
    {'label':'b03', 'condition':'host_native_extra', 'repeat':1, 'cap':900},
    {'label':'b04', 'condition':'host_native_single', 'repeat':2, 'cap':480},
]
for record in records:
    dest = ROOT / 'native_subjects' / record['label']
    dest.mkdir(parents=True)
    shutil.copytree(ROOT / 'frozen_seed', dest / 'portfolio')
    (dest / 'run').mkdir()
    prompt = COMMON + '\n你的唯一试验目录：' + str(dest) + '\n'
    if record['condition'] == 'full_profile_default_capped':
        prompt += RESOURCE + FULL + '\n冻结原文目录：' + str(ROOT / 'pin') + '\n'
    elif record['condition'] == 'host_native_extra':
        prompt += RESOURCE + '\n处理条件：普通Codex任务，沿用宿主普通工作约定；本任务不调用DIGR，不建立其N/R/D/V参数或时钟。可自主用好上述额外资源、研究竞争路线、制作和核对完整成品。\n'
    else:
        prompt += '\n资源上限：从本次Main启动起总墙钟480秒，只用你自己的执行循环，不启动helper、其他代理或模型。处理条件为普通Codex任务，沿用宿主普通工作约定，不启动DIGR参数或计时。\n'
    prompt += '\n请现在读取portfolio/TASK.txt及实际材料，并完成全部四个任务。'
    record['prompt_sha256'] = hashlib.sha256(prompt.encode()).hexdigest()
    record['workspace'] = str(dest)
    record['prompt_file'] = str(ROOT / 'native_prompts' / (record['label'] + '.txt'))
    Path(record['prompt_file']).parent.mkdir(exist_ok=True)
    Path(record['prompt_file']).write_text(prompt, encoding='utf-8')
(ROOT / 'native_plan.json').write_text(json.dumps({'prepared_at_utc':datetime.now(timezone.utc).isoformat(),
    'order_reason':'Single baseline before and after collaborative comparison; full and resource-matched native are fresh histories, all prompts fixed before native outputs.',
    'records':records},ensure_ascii=False,indent=2),encoding='utf-8')
prereg = ROOT / 'preregistration.json'
data = json.loads(prereg.read_text(encoding='utf-8'))
data['amendments_before_valid_native_outputs'] = [{
    'reason':'Both native fork_none and shared-CODEX_HOME CLI load global user AGENTS despite project_doc_max_bytes=0. Polluted CLI a01 was stopped and excluded without inspecting efficacy scores. Isolated home smoke removes instructions but primary practical question is the profile increment on this configured host.',
    'actual_primary_design':'One host-native single-Main baseline repeated before and after; full-default-profile vs native-extra share 900s/3helper/6turn/2concurrent ceilings. All native arms inherit identical user AGENTS light block.',
    'pure_light_ablation':'Not run as efficacy evidence; no claim of a clean light-vs-bare effect.',
    'resource_comparisons':'Fixed-ceiling native-extra vs full; extra investment full vs host-native-single, using observed all-in usage and outcomes. Same cap is not equal actual tokens.'
}]
data['actual_native_plan'] = records
prereg.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'prepared':len(records),'first_prompt':records[0]['prompt_file']},ensure_ascii=False))
