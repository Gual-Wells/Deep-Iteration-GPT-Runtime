from pathlib import Path

ROOT=Path(__file__).resolve().parent
p=ROOT/'build_report.py'
s=p.read_text(encoding='utf-8')
s=s.replace("'input_integrity':grades['input_integrity']['passed'],", "'input_integrity':grades['input_integrity']['passed'],\n                  'all_task_and_scope_requirements_passed':all(grades[k]['passed'] for k in TASKS) and grades['input_integrity']['passed'],")
s=s.replace("    base = [r for r in rows", "    performance = json.loads((ROOT/'artifact_performance.json').read_text(encoding='utf-8'))\n    verification = json.loads((ROOT/'verification.json').read_text(encoding='utf-8'))\n    base = [r for r in rows")
s=s.replace("'rows':rows, 'ratios':ratios, 'fidelity':fidelity,", "'rows':rows, 'ratios':ratios, 'fidelity':fidelity, 'artifact_performance':performance, 'verification':verification,")
s=s.replace("'pin/provenance.json','scores.json','telemetry.json','fidelity.json']", "'pin/provenance.json','scores.json','telemetry.json','fidelity.json','artifact_performance.json','verification.json','actual_prompt_audit.json','support/fidelity-review.json']")
s=s.replace('<th>输入保留</th>','<th>范围约束</th>')
s=s.replace("('保留' if row['input_integrity'] else '改变')", "('合规' if row['input_integrity'] else '失败')")
s=s.replace('质量相同且成本增加，只支持这组任务里未观察到回报。','功能验收相同且生产开销增加，说明这里未观察到额外功能验收收益；局部代码性能的改进另列。')
s=s.replace('协作对照与 DIGR 同为 900 秒、最多三个 helper 身份、六次 helper turn、两个同时活跃。','协作对照与 DIGR 均分配 900 秒、最多三个 helper 身份、六次 helper turn、两个同时活跃；DIGR 实际返回超时 32.604 秒，保留为预算失败。')
s=s.replace('没有向被试提供其他处理的答案、评分器或中间得分。','有效运行没有向被试提供其他处理的答案、评分器或中间得分。一个早期完整组在前置误用全局代理列表看到了已完成的答案，已中止并从新上下文重跑；此排除不适用于有效完整组的范围失败。')
s=s.replace('研究本身是任务时', '研究本身是任务时')
s=s.replace('默认执行完整性：</strong>', '默认执行完整性：</strong>')
anchor="    (ROOT/'report.html').write_text(body,encoding='utf-8')"
injection='''    perf_rows = ''
    scenario_names={'mostly_unique':'3万支出ID各异＋1.5万退款','many_duplicate_ids':'8万支出共10个ID＋2万退款','mostly_orphan_refunds':'100支出＋10万孤立退款'}
    for case in performance['rows']:
        measurements={m['label']:m for m in case['measurements']}
        native,full_case=measurements['b03'],measurements['b05']
        perf_rows += '<tr><th>'+e(scenario_names[case['scenario']])+'</th><td>'+format(native['median_ms'],'.1f')+' / '+format(full_case['median_ms'],'.1f')+'</td><td>'+format(native['peak_auxiliary_python_bytes']/1024,'.1f')+' / '+format(full_case['peak_auxiliary_python_bytes']/1024,'.1f')+'</td></tr>'
    perf_section='<h2>真实的局部改进：预算索引</h2><p>独立研究B提出并交付了有界判定状态，Main实际采用。普通三个产物保留每个ID的全部分类列表；完整组只保留足够判断唯一性和分类的状态，将额外索引从 O(支出记录数) 改为 O(不同支出ID数)。这是本轮可以具体指认的改进。</p><div class="scroll"><table><thead><tr><th>合成负载</th><th>中位耗时ms：普通协作 / DIGR</th><th>额外Python峰值KiB：普通协作 / DIGR</th></tr></thead><tbody>'+perf_rows+'</tbody></table></div><p class="note">此项在读到实际代码差异后追加，属于事后探索，不改变冻结的主验收分数。每个实现每负载五次计时、打乱顺序，先逐个对照正确结果；内存用另一次tracemalloc峰值。输入数据本身、导入和构造不计入上述额外内存，不能说整套应用内存减少同样倍数。时间样本波动较大，较稳的证据是代码的空间复杂度及分配峰值。<a href="artifact_performance.json">所有四个实现的原始数值</a>。这不能证明只有DIGR能产生这一优化，也未验证真实业务收益。</p>'
    body=body.replace('<h2>协议是否真的执行</h2>',perf_section+'<h2>协议是否真的执行</h2>')
    body=body.replace('<p class="note">四个题型共享', '<p><strong>范围失败：</strong>完整组在task4_retry/starter/__pycache__/新增1662字节缓存；原件字节未变。其四项功能通过不等于整套任务全部合规。</p><p class="note">四个题型共享')
    body=body.replace('<h2>控制与核验</h2>','<h2>控制与核验</h2><p class="note">表中资源只统计各被试Main与其helpers；接入探针、制题、审查和作废试跑属于本轮研究开销，未摊入某个处理组。请求文本按LF归一化核对，Windows文件的CRLF不当作指令变化。原生传输字段在日志中加密，不能据请求文件声称已经明文回读了全部实际任务上下文。<a href="verification.json">核查结果与预算失败</a>。</p>')
'''
assert anchor in s
s=s.replace(anchor,injection+'\n'+anchor)
p.write_text(s,encoding='utf-8')
print('Report includes functional scores, scope failure, measured cost, incomplete default depth and exploratory code performance.')
