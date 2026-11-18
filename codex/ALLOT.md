# Allot：原生宿主中的薄档位调度

Allot在有意义的任务块前，根据实际工作、难点和已有返回选择模型投入；不为每个命令另造一次调度。原生Main/D/V职责、DIGR五档投入与model/effort是独立的轴。不得把Less直接映射Low、把Max预设映射模型Max，或把D一律当廉价劳务。

常态起点是：步骤完整且边界确定的机械操作可用Low；明确规格的维护可用Medium；回应、困难分析与综合用High。实际高价值问题在High仍未收敛时选择XHigh；XHigh后支配性问题仍未解时可用Max。单次命令失败不构成升级理由。当前用户明确模型/effort优先，未授权自主降低时不从当前投入暗降；风险控制依赖真实工程条件，不靠Max代替回滚或权限。

`python -B tools/codex.py allot plan --root TASK --input block.json --catalogue model-list.json`读取真实宿主model/list或原生模型缓存。输入含安全block_id、model、kind、evidence，可带requested_effort、minimum_effort、current_effort、allow_downshift、unresolved、failed_efforts、high_value。模型/effort不可用时明确阻止该选择，不静默换模型或降档。kind为routine时须fully_specified=true。

plan输出可直接用于原生独立代理的`host_payload`，含fork_turns=none、model、reasoning_effort。宿主将该配置实际传给原生工具，保留独立上下文。若宿主不支持切换当前Main，本工具不能改变它；继续当前配置或在真实可用的独立执行上下文中承担相应任务，并报告实际状态。不得改写全局config冒充本次Main已经切换。

选择文件不是执行回执。取得实际宿主模型与effort后，用`allot observe --root TASK --block-id ID --input observation.json`保存实际model/effort/source_ref及是否匹配。native任务选择、能力来源、真实执行分别可辨；来源由操作者实际核对，工具不认证身份。`allot inspect`可在任务结束后读取。

本机只做选择与公开事实记录，模型工作仍由原生宿主执行；不新增OpenAI API或Claude调用，不创建订阅外费用。粗计量按USAGE，不凭effort名预设High/Max美元或额度倍数。
