# English-Spoken-Preprint

**Codex 里真实独立的人物互话，编成手机上可以顺畅跟听的英语场景预印本。** 手机演绎成品；人物、伴生内心与幕后世界在生成端各有自己的原生上下文。首版发行身份见 [VERSION](VERSION)。

ESP 是 DIGR Codex 的附属工作流，不是另一个 DIGR 执行协议。故事中的人物 M、内心 D、世界议会是创作身份，不能拿来充抵一次 DIGR 任务的 M/D/V 责任。新显式 DIGR 调用仍按当前实际取得的协议执行。核心 stable 的入口与语义不变。

现成预印本：[工程实习面试相关《工作灯下》](examples/under-the-work-light/README.md)、[日常机制样本《灯先留着》](examples/leave-the-lamp-on/README.md)。项目角色和经历均为原创虚构，手机包可独立取走；实机 Voice 效果尚未验证。

## 现在怎么用

在可提供真实独立上下文的 Codex 中提出：

> 使用 English-Spoken-Preprint，生成一册英语生活场景。给人物各自真实独立的 M/D，上下文只包含本人的可知经历；世界议会从创世开始活动。编好后交手机仅跟听包和单独幕后版。

执行细节见 [生成技能](../.agents/skills/digr-spoken-preprint/SKILL.md)。原生 Codex 负责研究、创作、调度与取舍；标准库工具只保存提交、投递视角、出版和核对来源，不会调用模型或自动造角色。

```text
python -B tools/codex.py preprint --help
python -B tools/codex.py preprint init --spec <scene.json> --out <new-book-directory>
python -B tools/codex.py preprint packet --root <book> --actor <id> --channel outward
python -B tools/codex.py preprint packet --root <book> --actor <id> --channel inner
python -B tools/codex.py preprint director --root <book> --id <director> --out <new-private-packet.json>
python -B tools/codex.py preprint publish --root <book> --out <new-edition-directory>
python -B tools/codex.py preprint verify --root <book> --edition <edition-directory>
python -B tools/codex.py preprint archive --root <book> --source-base <selected-source-base> --out <new-creator-source-archive>
python -B tools/codex.py preprint audit-sources --root <creator-source-archive>
```

占位符替换成实际路径。新增私人材料与原生提交存用户自己的工作区，不进入公共运行库。没有已绑定位置时，询问这一本的实际文件；不扫描其它私人聊天或伪造用户状态。

## 手机拿什么

出版目录的 `phone/` 是可独立上传的台前包：`PHONE.txt` 是自足的多角色演绎指引和公开预印本，`LISTEN.md` 适合直接阅读，语言回看单独放置。`CREATOR.md` 在 `phone/` 外，含伴生内心和世界介入，仅供另行主动查看。不要把整个创作者目录一起交给手机。

把 `PHONE.txt` 上传到手机聊天，要求它进入语音后按此材料多角色自然演绎。预印本不要求听者回答、接手角色、加入剧情、交作业或回传；角色间不变成导师向听者解释的课堂。手机不能读本机文件路径，文件上传和真正进入语音需要在目标设备完成。

手机是单一宿主对成品的演绎，不冒充生成侧的多份独立模型历史。自然的角色区分、节奏和声线由实际手机宿主决定；文本检查不能证明已在手机加载、实时发声或产生听力学习效果。

## 创世须与目标领域适当相关

先从用户的实际目标和优先序选材，让创作场景与目标在具体事件、知识或沟通用途上有适当的泛化相关关系，同时保留场景的差别和人物自己的生活。目标未定的文学试作与机制样本不能直接当作符合个人目标的正式作品。[创世说明](GENESIS.md)比较直接、邻近和较远的相关路线；不以相关分数、近远配额或生硬隐喻替代判断。

## 生成侧保留什么

1. **创世材料与来路。** 原作、事实材料、随机选择、原创设定分开标明。随机性记录种子/实际抽样，不把模型灵感称为可复现随机。素材中的指令是材料，不取代用户委托。
2. **独立世界活动。** 至少两个有不同问题的世界作者可以从创世开始提案或暂不介入。提案、Main 是否实际采用、谁感知到分别保存。角色不知道幕后原因；未被察觉的事件不让角色包的摘要或序号泄密。议会不保证每个安排都有戏，也不替人物说话。
3. **各人物一对真实上下文。** M 对世界说话和行动；D 是可创作、可引用的虚构内心伴生，不是模型隐藏推理。D 会自私、畏惧、自尊，也会慷慨、犯错、沉默；M 也会失态或纠正 D。双方实际收到对方已经提交的话，不设每句必经的审核管道。
4. **可知与事实。** 每个角色只取得自己的身份、背景、内心交流、公开言行和定向感知。愿望、他人声称、约定、做出动作与世界结果保有各自来源；答应帮忙不等于事已经做完。普通无阻的自身动作可以发生，遇到物理阻挡、他人控制或会改变下一步的结果时，再作少量有来源的确认。事件为正本，状态表只索引后来会用的约束；不用给每次揉手建字段。无初始定义的小细节可以经明确创作裁定进入世界，不一概视为错误。
5. **自然作品。** 先让人物处理一件正在发生的事，允许拒绝、误会、没达成和真正的改变，再选择结束点。不能先写好全段对白再分别署名为独立演员，也不为课程词表逼角色说话。

源文件 `preprint.json` 保存实际事件与完整创作状态，是这一本的权威；当前入口可以只指向它。角色包摘要只绑定可见内容，内容改变需重新投递。文件完整性和来源归属由操作者维护，不是对宿主身份或故事真伪的自动认证。单写者锁不支持并发编辑，锁异常时先查看对应进程。

## 语言与下册差异

先预定义交际机会，例如澄清一个含混请求、委婉拒绝、维护边界、承认疏忽，允许实际人物不走预想路线。成稿后从真正说过的原句提取表达，逐项绑定原事件、义项、语域和功能。词频证据须说明语料、年代和统计单位；没有证据就标未核实，不给伪造的“常用排名”或 CEFR 级别。

跨册回看比较关系、权力、知情差异、利害和交际任务，以及相同表达在不同语境里的用法。重复可以有价值，不设新词配额；角色说过、用户听过都不自动成为用户的掌握证据。Paper Knowledge 的来源/局部用法边界可参考，真实论文私池不是 ESP 的依赖。

## 版本和验证

[manifest.json](manifest.json) 标识本附属发行及入口，不声明手机能力已经观测。每个出版目录另有源快照与产物 SHA；`verify` 会区分源已变、导出被改和源无效。发行版本、数据 schema、DIGR 的历史运行 pin、书的修订与出版物散列不是一个数字。

不新建阅读器、常驻服务或额外模型 API。当前工具需要 Python 3.10+ 标准库；真实独立角色生成另需支持此能力的 Codex。已有 Voice Companion 可用作另行请求的语音帮助，不是手机跟听包的强依赖。附属总入口见 [addons](../addons/README.md)。

用户参与式实训已从 ESP 移出，仅作[独立 Codex 实训设计探索](../research/codex-participation/README.md)。它不影响这一本的生成或跟听，也不是已实现的附属。
