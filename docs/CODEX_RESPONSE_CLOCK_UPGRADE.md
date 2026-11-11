# 0.8.1旁路候选：正文返回与共同访时

基于0.8.0的314e513d439829fa1159e6801d1421ed1e569e0a；本分支独立交付，供另一更新线选择性集成。不要在接收方活跃任务中改写P_run、原记录或已初始化参数。版本0.8.1是此候选身份，整合发布者可选新的统一版本并重建执行包。

## 已接受的三项决定

- 最终response正文固定“结果→关键变化→工作过程→核验与限制→参数”。过程为正文时间／工作表；禁用内嵌HTML、Page、附件或截图替代报告，任务产物可链接。
- T统计所有参与者含D/V的WORK+SOURCE区间并集；t为SOURCE并集。U0与正式分开，每M单算本线，COMMON只进全局。
- 缺End可按可见依据近似补点；有效边界、实际补录时刻分开并指向具体Begin。不补部分留缺口，正常配对不因缺单调钟身份或别处坏行整体作废。

## 实际入口

新会话的session-3只增加`visit_clock:{path,run_id}`与`return_schema:2`，没有运行timer状态。默认共用文件取DIGR_VISITS_PATH，或CODEX_HOME/digr-codex/visits.jsonl；本机数据在D盘。其他环境可明确指定`task create --visits <共享文件> --run-id <任务分组>`。

`python -B tools/codex.py visits begin/end/report/repair --help`是共同登记入口。子代理只拿同一文件、run、自己的actor/line，正常边界实采当前墙钟；修复需`--begin-id --at <带偏移的有效时刻> --basis <可见依据>`。登记不是继续执行授权，直接file接口不拦截宿主任务；`--root begin`才核对受管理的生命周期与前置决定。等待/停止仍由模型和实际代理及时End，不用文件伪造主机拦截。

`runtime.codex_visits`提供append_visit、read_visits、summarize_visits、run_projection。普通END按本run/line/actor开放段配对，修复可指向旧Begin而不关闭后来段。生产read/write共用短锁；重复事件去重，冲突、坏行、倒退和未闭合局部显示。summary的T/t包含接受补点，closed-only值仅供内部复算，默认不用两套值增加阅读负担。

返回输入schema2用五个Markdown字段：`result, key_changes, work_process, verification_limits, parameters`；另可选sources/artifacts。`return seal`保存选定正文，`return body`原样输出，模型须直接贴到最终response；`return close`收口。schema2不生成HTML/SVG报告。工作表可由`render_work_table`辅助生成，段内论证和代码仍由模型写；不用空模板凑五段。

快照绑定本run的去重投影，不散列整个共同文件：其他run追加或同事件重放不使本返回STALE，本run新事实会。未知归属坏行另报，不能宣称已知归属；不要把整个共享文件选为返回sources，从而重新引入跨任务失效。

## 兼容与界限

旧session/pin保持原语义；新writer读得懂旧会话，但旧writer会拒绝session-3。新任务必须schema2，schema1与历史timeline保留供旧pin使用。没有自动安装、全局迁移、付费API或常驻计时服务。

T/t是登记区间覆盖，非CPU成本、逐秒持续工作的认证或整任务完整历史。墙钟跳变、遗忘登记仍可能造成扰动；明显矛盾局部留缺口，有据近似不整体作废。正文校验与seal核对保存内容，不能确认模型已经把它发到聊天UI，更不证明任务品质或参数责任达标。

验证范围包含实际Windows多写者追加、持锁进程退出、损坏尾部、重放、定向修复、跨run投影，以及session→seal→CLI body→close路径。研究与工程两类正文小样都来自实际材料，未进行跨任务模型遵循率或读者效果实验。持续领域研究揭示的后续问题在合并前落实或明确保留，不以测试数量认定收益。
