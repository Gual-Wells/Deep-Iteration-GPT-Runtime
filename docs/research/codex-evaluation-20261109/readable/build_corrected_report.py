"""Build a corrected interpretation without rerunning subjects or changing raw data."""
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def build():
    def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
    correction=read('interpretation_correction.json')
    previous=read(correction['archive_relative']+'/results.json')
    fidelity=read('fidelity.json')
    performance=read('artifact_performance.json')
    rows=previous['rows']
    for row in rows:
        if row['label']=='b05':
            row['name']='默认目标文本＋外部裁剪的模拟运行'
            row['evaluation_status']='externally censored simulation; default-profile efficacy not evaluable'
        else:row['evaluation_status']='completed native reference observation'
    source_names=['scores.json','telemetry.json','artifact_performance.json','preregistration.json','native_plan.json','interpretation_correction.json','fidelity.json','support/suite.py','support/fidelity-review.json','build_report.py','build_corrected_report.py']
    data={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'pin':previous['pin'],
          'status':'CORRECTED: default-profile inferences withdrawn',
          'default_profile_efficacy_evaluable':False,
          'conclusion':fidelity['user_facing_conclusion'],'correction':correction,
          'rows':rows,'descriptive_prefix_ratios_only':previous['ratios'],
          'ratio_interpretation':'These ratios compare an observed truncated trajectory with completed reference trajectories, not complete-default cost or efficiency.',
          'fidelity':fidelity,'artifact_performance':performance,
          'historical_harness_checks':previous['verification'],
          'harness_check_interpretation':'Original external-cap checks are historical instrument checks, not DIGR T/t compliance or protocol failure.',
          'artifact_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_names}}
    (ROOT/'results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    def e(value):return html.escape(str(value))
    table_rows=''.join('<tr><th>'+e(row['name'])+'</th><td>'+str(row['tasks_passed'])+'/4</td><td>'+format(row['wall_seconds']/60,'.2f')+'</td><td>'+format(row['uncached_input_plus_output'],',')+'</td><td>'+('边界符合' if row['input_integrity'] else '新增缓存越界')+'</td></tr>' for row in rows)
    perf_rows=''
    scenarios={'mostly_unique':'3万支出ID各异＋1.5万退款','many_duplicate_ids':'8万支出共10个ID＋2万退款','mostly_orphan_refunds':'100支出＋10万孤立退款'}
    for case in performance['rows']:
        m={row['label']:row for row in case['measurements']}; a,b=m['b03'],m['b05']
        perf_rows+='<tr><th>'+e(scenarios[case['scenario']])+'</th><td>'+format(a['peak_auxiliary_python_bytes']/1024,'.1f')+' / '+format(b['peak_auxiliary_python_bytes']/1024,'.1f')+'</td></tr>'
    archive=e(correction['archive_relative'])
    body="""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DIGR实验更正：默认配置比较结论撤回</title><style>
body{max-width:1080px;margin:34px auto;padding:0 22px 60px;font:16px/1.75 system-ui,"Microsoft YaHei",sans-serif;color:#172438;background:#f7f9fc}h1{font-size:29px;line-height:1.4}h2{font-size:22px;margin-top:32px}.notice{background:#fff5de;border-left:5px solid #a9610b;padding:18px 22px;border-radius:5px}.lead{font-size:19px}.note{font-size:14px;color:#526178}table{width:100%;border-collapse:collapse;background:white;font-size:14px}td,th{text-align:left;padding:10px 12px;border-bottom:1px solid #dfe5ef}thead th{background:#e9eef8}.scroll{overflow:auto}a{color:#244fa5}code{font-size:13px;overflow-wrap:anywhere}li{margin:9px 0}details{background:white;padding:12px 18px;margin-top:14px}
</style><h1>DIGR实验更正：原默认配置比较不成立</h1>
<section class="notice"><strong>已撤回原判断</strong><p class="lead">用户指出的设计问题成立。我保留默认N12/R4/D3/V3，却在函数头之外另加900秒和代理配额限制，再根据未完成参数评价默认配置。这不能支持“默认深执行偏重”或对最低次数的负面判断。</p><p>实际使用的是协议文本模拟，没有真正用显式DIGR(...)函数头声明受控配置。当前结论应为：<strong>这次实验没有正确检验默认DIGR，整体效果仍待有效比较。</strong></p></section>
<h2>错误具体在哪里</h2><ul>
<li>默认目标与外部时限、helper数量及turn配额同时施加，没有先证明它们相容。参数不足属于被实验设计截断的观测，不能归责为协议失败。</li>
<li>把截断片段已消耗的时间/token与普通组完成运行的消耗相除，只能描述这几段观测；不能当作完整默认DIGR的投入产出估计。</li>
<li>外部全程墙钟还混入了前置和独立代理工作。0.7.0协议对前置、T/t和D/V独占活动另有范围约定，研究者的900秒不等于协议正式T/t。</li>
</ul><h2>仍可保留的事实</h2><p>以下只保留原始观测，不再排列为默认协议的优劣评估。所有条件共享现有轻量AGENTS，模型标签为gpt-6.1-sol / max；四类题目均为固定合成任务。</p>
<div class="scroll"><table><thead><tr><th>历史运行</th><th>功能验收</th><th>观测墙钟/分</th><th>未缓存输入＋生成</th><th>任务写入边界</th></tr></thead><tbody>"""+table_rows+"""</tbody></table></div>
<p class="note">模拟组的15.54分钟是被外部裁剪的过程片段，不能标成完成默认配置的耗时。“超出900秒32.604秒”仍是仪器观测，不再列为DIGR协议失败。新增1662字节缓存是独立的任务范围问题；原始输入字节未改变。</p>
<h2>局部代码改进仍然成立</h2><p>独立研究提出有界的expense id判定状态，Main实际采用。与普通协作组保存分类列表相比，额外索引空间从O(支出记录数)变为O(不同支出ID数)。代码、原始功能检查和事后性能探针均保留。</p>
<div class="scroll"><table><thead><tr><th>合成负载</th><th>额外Python峰值KiB：普通协作 / 模拟组</th></tr></thead><tbody>"""+perf_rows+"""</tbody></table></div><p class="note">输入本体不计入额外内存。该探针是在读到代码差异后追加的探索性测量，不能证明只有DIGR能产生该改进，也不能替代默认协议的有效对照。<a href="artifact_performance.json">原始数据</a>。</p>
<h2>正确的两种比较</h2><ol>
<li><strong>评估完整默认配置：</strong>以真实默认调用进入，遵守取得的协议及参数语义，让责任完整履行，再比较产物和总资源。真实资源原因不得不停止时，标为截断，不拿参数缺口批评默认配置。</li>
<li><strong>评估受控配置：</strong>执行前就在DIGR(...)函数头明确本轮N/T/R/S/D/V/L/M等参数，以适合任务的完整配置做对照；不能在运行后把N6/R2/D1/V3倒填成旧实验的调用头。</li>
</ol><p class="note">在这次冻结的0.7.0中，target=15min是软目标，min=15min是硬下限，都不是“15分钟到点强制结束”的函数头语义。详见<a href="pin/codex/PARAMETERS.md">本次冻结参数原文</a>。本次更正没有启动新一轮试验，也没有事后修改原调用、目标、原始数据或评分器。</p>
<h2>更正与原记录</h2><p><a href="interpretation_correction.json">逐项更正及撤回判断</a> · <a href="results.json">当前结果及有效性说明</a> · <a href="scores.json">原始验收</a> · <a href="telemetry.json">原始数值用量</a> · <a href="preregistration.json">原预注册及历史修订</a></p>
<details><summary>此前解释已归档，原件保留</summary><p><a href=\""""+archive+"""/report.html">原报告（解释已撤回）</a> · <a href=\""""+archive+"""/results.json">原结果文件</a> · <a href=\""""+archive+"""/archive_manifest.json">逐文件归档SHA256</a></p><p>归档用于追溯旧错误，不代表当前观点。当前入口始终是此报告。</p></details></html>"""
    (ROOT/'report.html').write_text(body,encoding='utf-8',newline='\n')
    print(json.dumps({'report':str(ROOT/'report.html'),'default_profile_efficacy_evaluable':False,'archive':correction['archive_relative']},ensure_ascii=False))

if __name__=='__main__':build()
