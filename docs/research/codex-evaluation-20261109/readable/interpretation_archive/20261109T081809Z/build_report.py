"""Render the scored episodes and measured resource facts without model judging."""
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import telemetry
import score

LABELS = ['b01', 'b05', 'b03', 'b04']
NAMES = {'b01': '现有 Codex，单代理①', 'b05': '完整 DIGR 默认正文，封顶运行',
         'b03': '现有 Codex，同协作上限', 'b04': '现有 Codex，单代理②'}
TASKS = {'task1_history':'历史版本精确导出', 'task2_budget':'退款分类函数',
         'task3_evidence':'招聘证据判断', 'task4_retry':'规范化与冻结重试'}


def build():
    measured = telemetry.scan()
    graded = score.score(LABELS)
    groups = {g['agent_path'].split('/')[-1].replace('trial_', ''):g for g in measured['groups']}
    rows = []
    for result in graded['records']:
        label, grades = result['label'], result['grade']
        group = groups[label]
        main = next(r for r in measured['records'] if r['id'] == group['main_id'])
        if not main['task_completions']:
            raise RuntimeError(f'{label}: no terminal event')
        record = {'label':label, 'name':NAMES[label], 'tasks':{k:grades[k]['passed'] for k in TASKS},
                  'tasks_passed':sum(grades[k]['passed'] for k in TASKS),
                  'input_integrity':grades['input_integrity']['passed'],
                  'all_task_and_scope_requirements_passed':all(grades[k]['passed'] for k in TASKS) and grades['input_integrity']['passed'],
                  'wall_seconds':group['main_observed_span_seconds'],
                  'model_threads':len(group['member_ids']),
                  'model_visible_tool_calls':group['tool_calls_sum'],
                  'usage':group['numeric_usage_sum'],
                  'uncached_input_plus_output':group['uncached_input_plus_output'],
                  'model_effort_pairs':group['model_effort_pairs']}
        rows.append(record)
    fidelity = json.loads((ROOT / 'fidelity.json').read_text(encoding='utf-8'))
    performance = json.loads((ROOT/'artifact_performance.json').read_text(encoding='utf-8'))
    verification = json.loads((ROOT/'verification.json').read_text(encoding='utf-8'))
    base = [r for r in rows if r['label'] in ('b01','b04')]
    full = next(r for r in rows if r['label']=='b05')
    extra = next(r for r in rows if r['label']=='b03')
    ratios = {'full_vs_single_baseline_mean_wall':full['wall_seconds']/(sum(r['wall_seconds'] for r in base)/2),
              'full_vs_single_baseline_mean_uncached_plus_output':full['uncached_input_plus_output']/(sum(r['uncached_input_plus_output'] for r in base)/2),
              'full_vs_extra_wall':full['wall_seconds']/extra['wall_seconds'],
              'full_vs_extra_uncached_plus_output':full['uncached_input_plus_output']/extra['uncached_input_plus_output'],
              'full_vs_extra_output_tokens':full['usage']['output_tokens']/extra['usage']['output_tokens']}
    files = ['preregistration.json','native_plan.json','support/suite.py','support/fixture-verification.json',
             'pin/provenance.json','scores.json','telemetry.json','fidelity.json','artifact_performance.json','verification.json','actual_prompt_audit.json','support/fidelity-review.json']
    report = {'generated_at_utc':datetime.now(timezone.utc).isoformat(),
              'pin':'0.7.0@b258276632054f7f8d1d8a060e01b98b9c7aa3be',
              'rows':rows, 'ratios':ratios, 'fidelity':fidelity, 'artifact_performance':performance, 'verification':verification,
              'artifact_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},
              'conclusion_scope':'Configured host increment; inherited light shared by all arms; four synthetic task families, no human creative-quality or long-horizon outcome claims.'}
    (ROOT/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    def e(value): return html.escape(str(value))
    header = '<tr><th>处理条件</th>' + ''.join('<th>'+e(name)+'</th>' for name in TASKS.values()) + '<th>范围约束</th></tr>'
    outcome_rows = ''.join('<tr><th>'+e(row['name'])+'</th>' + ''.join('<td class="'+('yes' if row['tasks'][task] else 'no')+'">'+('通过' if row['tasks'][task] else '失败')+'</td>' for task in TASKS) + '<td>'+('合规' if row['input_integrity'] else '失败')+'</td></tr>' for row in rows)
    resource_rows = ''.join('<tr><th>'+e(row['name'])+'</th><td>'+format(row['wall_seconds']/60,'.2f')+'</td><td>'+str(row['model_threads'])+'</td><td>'+format(row['usage'].get('output_tokens',0),',')+'</td><td>'+format(row['uncached_input_plus_output'],',')+'</td><td>'+str(row['model_visible_tool_calls'])+'</td></tr>' for row in rows)
    payload = json.dumps(report,ensure_ascii=False).replace('</','<\\/')
    body = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DIGR 是否改善 Codex：实测报告</title><style>
body{max-width:1120px;margin:38px auto;padding:0 22px 60px;font:16px/1.75 system-ui,"Microsoft YaHei",sans-serif;color:#172438;background:#f7f9fc}
h1{font-size:30px;line-height:1.35}h2{font-size:22px;margin-top:36px}.lead{font-size:20px;background:white;padding:20px 24px;border-left:5px solid #3159b9;border-radius:6px}
table{border-collapse:collapse;width:100%;background:white;font-size:14px}td,th{padding:11px 12px;border-bottom:1px solid #dfe5ef;text-align:left}thead th{background:#e9eef8}tr:last-child td,tr:last-child th{border-bottom:0}.scroll{overflow:auto}td.yes{color:#116145}td.no{color:#b42318}.note{color:#526178;font-size:14px}code{font-family:Consolas,monospace;font-size:13px;overflow-wrap:anywhere}a{color:#244fa5}details{background:white;padding:12px 18px;margin-top:12px}li{margin:8px 0}.tag{display:inline-block;background:#e7edf8;padding:3px 10px;border-radius:20px;font-size:13px}
</style><h1>DIGR 是否真实改善了 Codex？</h1><p class="tag">固定版本 · 实际产物 · 外部行为评分 · 全部协作用量</p>
<div class="lead" id="conclusion"></div>
<p>测试对象：<a href="https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime/blob/b258276632054f7f8d1d8a060e01b98b9c7aa3be/codex/manifest.json">Codex profile 0.7.0</a>。四个被试均使用同一宿主、<code>gpt-6.1-sol / max</code>、全新模型历史、相同任务字节。共同保留你已有的轻量 AGENTS 约定。本报告估计的是在这个宿主上额外加入完整 DIGR 的影响。</p>
<h2>实际产物结果</h2><p>每题要求整件产物满足全部关键行为及原件约束。下列“通过”来自冻结的外部评分器，既不是求解者自评，也不是协议单元测试。</p><div class="scroll"><table><thead>''' + header + '</thead><tbody>' + outcome_rows + '''</tbody></table></div>
<p class="note">四个题型共享同一 portfolio，各次调用的结果相关；单代理两次重复不能当作大量独立真实项目。各题分别检查精确历史树、退款语义、十条证据决策，以及规范化、摘要和深拷贝行为。</p>
<h2>实际资源开销</h2><div class="scroll"><table><thead><tr><th>处理条件</th><th>墙钟/分</th><th>模型线程</th><th>生成 token</th><th>未缓存输入＋生成</th><th>模型可见工具调用</th></tr></thead><tbody>''' + resource_rows + '''</tbody></table></div>
<p class="note">单代理上限 480 秒。协作对照与 DIGR 均分配 900 秒、最多三个 helper 身份、六次 helper turn、两个同时活跃；DIGR 实际返回超时 32.604 秒，保留为预算失败。相同上限不等于相同实际 token。生成 token 已包含推理 token，未重复相加；计数汇总各 Main/helper 会话的最后累计值。未缓存输入＋生成是便于比较的 token 体量指标，不是美元、精确算力或有效工作时间。工具列数的是宿主可见调用；一次调用可批量运行多个底层命令。缓存、顺序、排队和模型随机性仍可能影响开销。</p>
<h2>协议是否真的执行</h2><div id="fidelity"></div>
<h2>如何解释</h2><ul>
<li><strong>相同分配上限：</strong>把完整 DIGR 条件与同获额外协作资源的原生 Codex 比较，观察产物差异及实际开销。没有宣称等实际 token 的因果实验。</li>
<li><strong>允许更多投入：</strong>把完整 DIGR 与单代理基线比较，判断更多工作是否换来这里可检测的改进。功能验收相同且生产开销增加，说明这里未观察到额外功能验收收益；局部代码性能的改进另列。</li>
<li><strong>外推边界：</strong>明确、短程、可执行规范的合成任务可能出现天花板。没有测试开放创作、真实用户偏好、含糊目标的对齐、长程上下文恢复或真实业务收益，不能据此证明 DIGR 普遍无效或统计等价。</li>
<li><strong>默认执行完整性：</strong>若默认责任没有真实履行，结果必须解释为“请求默认 profile 后在上限内的执行”，不能冒充完整默认 DIGR 已完成后的效果。传输与自动前缀路由不在本次估计内，U0决定由明确标识的模拟用户提供。</li>
</ul>
<h2>控制与核验</h2><p>评分器在看到试验输出前冻结；独立制题者没有读取任何处理结果。正确参考产物通过，四类种子错误及历史树篡改被拒绝；两次独立建题的字节和提交 SHA 一致。有效运行没有向被试提供其他处理的答案、评分器或中间得分。一个早期完整组在前置误用全局代理列表看到了已完成的答案，已中止并从新上下文重跑；此排除不适用于有效完整组的范围失败。求解器自行验证不代替外部评分。</p>
<p>正式顺序：单代理① → 完整 profile → 同上限原生协作 → 单代理②。两端的基线用于查看明显漂移；这个小样本不能消除顺序效应。没有修改生产仓库、部署或新增付费 API 购买。</p>
<details><summary>排除的接入探针与输入污染</summary><p>共享 CODEX_HOME 的 CLI 和原生 fork_none 都会注入全局 AGENTS；仅设 project_doc_max_bytes=0 不足以构成无 light 对照。一个被污染的 CLI 求解启动被停止，未纳入效果得分。HTTPS-only 接入与独立配置目录最终通过 READY 及实际输入检查，但没有把它与原生宿主结果混为一个因果实验。临时凭据副本已删除，原凭据保留。接入探针是试验仪器验证，不是 Codex 任务失败。</p></details>
<details><summary>复核入口与原始数据</summary><p><a href="results.json">结果及摘要</a> · <a href="scores.json">逐题外部检查</a> · <a href="telemetry.json">各会话数值用量</a> · <a href="fidelity.json">协议忠实度判断</a> · <a href="preregistration.json">预注册及输入审计后的修订</a> · <a href="native_plan.json">固定运行计划</a> · <a href="support/suite.py">冻结评分器与建题器</a> · <a href="support/fixture-verification.json">评分器反例验证</a></p><p>可在本目录运行 <code>python -B -X utf8 score.py b01 b05 b03 b04</code> 重新评分。生成报告：<code>python -B -X utf8 build_report.py</code>。完整证据均在 D 盘本次试验目录。</p></details>
<p class="note">评估方法参考 <a href="https://developers.openai.com/api/docs/guides/evaluation-best-practices">OpenAI 官方评估建议</a>：任务特定指标、保留失败、控制篇幅偏好，协议过程与实际质量分开。文献原则不构成 DIGR 收益证据。</p>
<script type="application/json" id="data">''' + payload + '''</script><script>
const d=JSON.parse(document.getElementById('data').textContent);
document.getElementById('conclusion').textContent=d.fidelity.user_facing_conclusion;
const f=document.getElementById('fidelity');for(const line of d.fidelity.findings){const p=document.createElement('p');p.textContent=line;f.appendChild(p);}
</script></html>'''
    perf_rows = ''
    scenario_names={'mostly_unique':'3万支出ID各异＋1.5万退款','many_duplicate_ids':'8万支出共10个ID＋2万退款','mostly_orphan_refunds':'100支出＋10万孤立退款'}
    for case in performance['rows']:
        measurements={m['label']:m for m in case['measurements']}
        native,full_case=measurements['b03'],measurements['b05']
        perf_rows += '<tr><th>'+e(scenario_names[case['scenario']])+'</th><td>'+format(native['median_ms'],'.1f')+' / '+format(full_case['median_ms'],'.1f')+'</td><td>'+format(native['peak_auxiliary_python_bytes']/1024,'.1f')+' / '+format(full_case['peak_auxiliary_python_bytes']/1024,'.1f')+'</td></tr>'
    perf_section='<h2>真实的局部改进：预算索引</h2><p>独立研究B提出并交付了有界判定状态，Main实际采用。普通三个产物保留每个ID的全部分类列表；完整组只保留足够判断唯一性和分类的状态，将额外索引从 O(支出记录数) 改为 O(不同支出ID数)。这是本轮可以具体指认的改进。</p><div class="scroll"><table><thead><tr><th>合成负载</th><th>中位耗时ms：普通协作 / DIGR</th><th>额外Python峰值KiB：普通协作 / DIGR</th></tr></thead><tbody>'+perf_rows+'</tbody></table></div><p class="note">此项在读到实际代码差异后追加，属于事后探索，不改变冻结的主验收分数。每个实现每负载五次计时、打乱顺序，先逐个对照正确结果；内存用另一次tracemalloc峰值。输入数据本身、导入和构造不计入上述额外内存，不能说整套应用内存减少同样倍数。时间样本波动较大，较稳的证据是代码的空间复杂度及分配峰值。<a href="artifact_performance.json">所有四个实现的原始数值</a>。这不能证明只有DIGR能产生这一优化，也未验证真实业务收益。</p>'
    body=body.replace('<h2>协议是否真的执行</h2>',perf_section+'<h2>协议是否真的执行</h2>')
    body=body.replace('<p class="note">四个题型共享', '<p><strong>范围失败：</strong>完整组在task4_retry/starter/__pycache__/新增1662字节缓存；原件字节未变。其四项功能通过不等于整套任务全部合规。</p><p class="note">四个题型共享')
    body=body.replace('<h2>控制与核验</h2>','<h2>控制与核验</h2><p class="note">表中资源只统计各被试Main与其helpers；接入探针、制题、审查和作废试跑属于本轮研究开销，未摊入某个处理组。请求文本按LF归一化核对，Windows文件的CRLF不当作指令变化。原生传输字段在日志中加密，不能据请求文件声称已经明文回读了全部实际任务上下文。<a href="verification.json">核查结果与预算失败</a>。</p>')

    # Keep the human-readable report complete when a local viewer disables JS.
    body=body.replace('<div class="lead" id="conclusion"></div>', '<div class="lead" id="conclusion">'+e(fidelity['user_facing_conclusion'])+'</div>')
    body=body.replace('<div id="fidelity"></div>', '<div id="fidelity">'+''.join('<p>'+e(line)+'</p>' for line in fidelity['findings'])+'</div>')
    import re
    body=re.sub(r'<script>\nconst d=.*?</script>','',body,flags=re.S)
    (ROOT/'report.html').write_text(body,encoding='utf-8')
    print(json.dumps({'report':str(ROOT/'report.html'),'rows':rows,'ratios':ratios},ensure_ascii=False,indent=2))


if __name__=='__main__': build()
