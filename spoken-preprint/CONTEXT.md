# 真实困难的场景边界

人物仍能推理、试探、误会和学习；个人经历和实际结果不能由一句话补造。ESP 的 U0/D/V 是创作身份，不充抵正式 DIGR 责任。

可选 actor `working_profile` 保存 basis、experience、working_knowledge、unestablished 字符串列表。这是有来源或明确虚构的角色描写，**不是知识白名单**。未知不意味着不会；推理不能变成未曾做过的测试。

actor `materials` 是 mid→{title,text,origin,access} 对象。access 默认 self；world 通过 access_key 的值 available 控制。packet 先给标题和状态，真实 outward speech/action 的 `reads:[mid]` 记录后才提供文本，不可用只返回 UNAVAILABLE。他人拿不到本人读取结果；材料离线不抹除先前交付内容。工具证明文本提供，不能证明模型认真读过。

真实个人材料可在事件开始前 bind-context，只给本册/本角色的选定 capsule，完整 profile 不发演员。新使用前用 Personal Context check-view 核对原件；旧书冻结资料仍可作为历史，不能叫今天有效。

## 世界后果

`frozen_world_keys` 指向 initial_state 中不可改写的重要过去。可选 `world_rules` 给 mutable_keys 和 monotone_decreasing（非负整数机会预算）；每个 director 声明 reads/writes。packet 只给该领域世界项，world 事件要有当前 director packet/executor 和实际来源。不能写其它领域、重写冻结历史或补回用掉的机会。

这些数值服务具体对象，不成为全书固定错误/失败配额。控制器仍核对语义：输出值是否来自所说的测试、账单月付是否已含旧余额。程序不读懂自然语言，也不认证诊断或公平。

## 既有身份的反馈扰动

可选 perturbation_defs：id、origin{kind:U0|D|V,id}、targets、scope、trigger、release、message、max_reactions。V 可列 blocks 中目标的材料 ID；D 只影响自己人物的心理条件，不移除物理材料、不公开替 M 行动。

`kind:perturbation` 事件带 perturbation_id/operation/origin/source_ref；D/V 还要当前 owner packet/executor。basis_event_ids 必须是 owner 真正可见的事件。作者先实际提出，控制器决定采用后记录；工具不自动调用作者或生成反驳。

- activate：创世定义或根据实际事件提出的新定义进入 active；U0 只能场前激活，不能中途借创世权威新增过去。
- react：实际见到新回应后改变 message；须新 basis，不能重复同一反驳，最多 max_reactions 次。
- resolve/retire：写处理结果或剩余代价，结束后不继续反驳；不等于自动成功。

幕后定义与成因不进手机；人物只得到自身条件或真正采用的感知。世界可以退让、暂不介入、保留代价，不为让人失败而无限追加障碍。
