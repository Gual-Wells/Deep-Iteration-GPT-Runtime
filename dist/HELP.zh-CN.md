# DIGR 5.0.0-Berta1 帮助

DIGR 是显式调用、单条消息内生效的高投入执行模式；不会自动延续到下一轮。

## 1. 宽捕获与 pinned STARTUP 分类

```text
DIGR/help
深度迭代/help
DIGR：<非空任务>
DIGR(<参数>)：<非空任务>
深度迭代：<非空任务>
```

`DIGR` 必须精确大写。本地层对 lstrip 后以 exact `DIGR`/`深度迭代` 开头的消息一律先真实获取仓库，不在本地判断 help、task、括号、标点、NATIVE 或 INVALID。取得 pinned manifest/VERSION 和 STARTUP 后，exact `/help` 才是 HELP；可配平可选参数组 + 冒号 + 非空任务是 EXECUTING；`DIGR是什么`、`DIGR 协议...`、`DIGRAPH` 由 pinned STARTUP 判为 NATIVE 并把完整原文交回普通 ChatGPT。`digr`、`Digr` 不捕获。空任务或坏括号返回修正提示，不建立 Run。

## 2. HostAdapter 与执行等级

仓库 STARTUP 分类 EXECUTING 后，使用 `digr.preflight` 做参数解析与能力协商；最终交付使用 `digr.commit_delivery`。模型不得伪造或自行认证 receipt。

若宿主缺少这些工具，只能提供标记为 `DIGR~` 的 ADVISORY 输出，需说明未执行的约束，不得附 canonical proof。HELP 不建立任务时钟。

## 3. Berta1 standard profile

公开参数顺序为 `N,T,R,B,S(n,t,r,b),D(s),V(o),L(e)`；默认值是 N2、R1、T0、B0、source-auto、S(0,0,0,0)、D0、V0、L1。显式类型标签允许乱序；平铺 `n/t/r/b/s/o/e` 可直接表示内部参数；删去显式项后，其余无标签参数必须仍有唯一解释，否则返回 AMBIGUOUS/INVALID，不猜测。V(0) 与 D(0) 都只是零下限。

V 是持久化远距视角通道：各自拥有私有 VLedger，不进行 V-to-V 通信；只有具备实质事件、语义距离、非冗余说明、Main 价值回传和正 V 时间的通道才计入 actual。Main 始终拥有最终策略与候选权。

四类时间为 `T=MAIN+SOURCE`、`t=SOURCE`、`D=D_EXCLUSIVE`、`V=V_EXCLUSIVE`，IDLE/META 均不计。交付时写出 TOTAL 以及 N/T/R/B/S/D/V/L 各独立本地 NDJSON 日志；本版本不要求 MCP、UI、PWA、远端桥或后端。

无参数、`standard`、`标准` 或 `profile=standard` 使用确定性合同：

```text
N=2, R=1, T=0（无时间要求）, source=auto, D=0, L=1
```

模型不会补全、左移或猜测参数。裸时间或 `min=<duration>` 表示 hard time minimum；`target=<duration>` 表示 soft target；时间必须带单位，0 的 hard minimum 无效。旧位置参数若能唯一解析，会自动按 `legacy-alpha4` 兼容路径处理并产生可见警告，无需 profile token。

## 4. N、R 与 Candidate

N 只计实质改变方案、表示、证据结论或验证方法的 MAIN evolution；机械改写不计。R 必须已有 Candidate，再把它送回整个解决过程挑战任务理解、假设、策略、来源、工具路线和验证。挑战后保留原 Candidate 可以，但必须有实质证据。

达到最低次数只打开停止资格；若继续工作仍能明显改善结果，应继续。

## 5. source=auto

模型根据任务决定外部来源是否能提高正确性，优先使用高价值、可靠、适当时为一手的来源。只有能证明来源无关、被用户禁止或宿主不可用时，才可记录 `WAIVED`；“模型已经知道”不是 waiver。

## 6. D(0) 与 L

`D(0)` 仅表示没有必须完成的 D 下限，绝不关闭 D。若非局部挑战能改善结果，模型仍可执行 D，actual 可大于 0。D 必须经过 proposal、Decree、执行与 MAIN reintegration。

L1/L2/L3 是隔离等级目标。宿主能力不能自动升级为 `L_actual`；实际等级必须绑定具体 intervention receipt。没有 completed D 时，L actual 可保持未知。

## 7. 时间

Standard profile 没有时间要求。显式 hard minimum 需要连续可信单调时钟；能力不足时 preflight 必须阻断或如实降级。只计实质 MAIN/SOURCE 工作；等待、sleep、工具排队、META、日志、机械改写和 exclusive D 不计时，也不得填充时间。

## 8. Manifest 导航与启动

所有宽捕获候选都先访问仓库。已有 connector 可读取 current `stable` branch HEAD；direct REST 必须同轮读取 branch 与 Git-ref 并要求完整 SHA 一致。取得 SHA 后先读取 pinned `manifest.json` 与 `VERSION` 并验证版本一致，再完整加载 manifest 的唯一 `startup_slice`。只有 pinned STARTUP 能分类 NATIVE/HELP/INVALID/EXECUTING。

`manifest.json` 是导航权威。其声明的 runtime descriptor 仅描述并校验生成的执行/发布 artifact；每个所用 artifact 仍须按 `sha256`、`byte_length` 和 `media_type` 校验，但 descriptor 不能替代 manifest/STARTUP 导航。

## 9. 交付与证明

最终结果必须以 exact bytes、media type 和 current Candidate binding 调用 `digr.commit_delivery`。交付是两阶段、fail-closed、可恢复的提交：先准备并验证 payload/summary/proof/envelope，再转入 `DELIVERED`；中途失败保持非成功。只有 verified `DELIVERED` 才能输出 canonical proof。交付门未满足时关闭为 `INCOMPLETE`。

正常回答不泄露隐藏推理、内部日志或工作区细节。
