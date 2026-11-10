# DIGR Voice Companion · 0.1.0

让语音伙伴能帮你想出、说出并继续发展一段内容。它可以直接给一个观点、一段回应或一起创作，不把帮助限制成纠错和半句提示。

这是DIGR库的附属会话设施，有自己的版本，不是新的DIGR执行通道。Codex和stable的显式路由、参数、真实独立代理及计时语义均保持原义。

## 日常怎样用

- 宿主明确提供实时Voice状态时，设施后台待命；不把所有语音请求强制变成英语课。
- 通道不明时，首次说“进入语音陪练”或“Start voice rehearsal”，本会话便可练。只有文本转录不能证明麦克风开着。
- 卡住时说 **Coach, help me out**。完整的 **sorry please your turn** 也兼容；裸sorry、please、your turn只是普通话语，不是子串指令。
- 默认用英语说明此刻可做的交流/创作动作，再给可直接借用的英语。可以要求更简单、完整示范、一起写，或继续帮你想。
- 用户贡献了新内容，伙伴接住它继续。普通任务、明确退出和可信的通道切换按实际意图处理，不把学习模式强加给它们。

全局短入口本身有最低帮助能力。完整技能与例子可以增强它，但没有加载全文、没有工具时也不先停下来取库。

## 手机上直接使用

1. 将 [RESIDENT.txt](RESIDENT.txt) 的内容合并到 ChatGPT 自定义指令，保留原有指导。这是全局待命层；项目内也可放在项目指令中。
2. 把 [完整英文单文件](ChatGPT-Voice-Companion.md) 上传到需要练习的 ChatGPT 项目或对话。它已包含行为、示例及技术世界，不需要手机读本地目录。
3. 第一次发送 [START.txt](START.txt) 的一句话，明确选用附件并进入陪练；随后使用 Voice。已处于可确认的 Voice 且有当前话题时，无需每轮再开启。

短常驻核可独立救场；全文让伙伴有更多内容与方法。只粘贴全文不是绕过附件读取的办法，长文本可能被界面转换成附件。用 START 明确让模型读取核心指导，示例仍按需。若只想练当前聊天，可以先放短核并说“进入语音陪练”。

## 本地使用和重新导出

将 `.agents/skills/digr-voice-companion` 整个目录安装到宿主支持的用户技能位置；本机数据实体放 D，必要的用户路径入口使用目录联接。安装后的新会话可以发现该技能；是否实际选用仍看会话。全局短核可合并进有效的 `CODEX_HOME/AGENTS.md`，不要另建一个冲突的 DIGR 路由。

在本仓库中可重新导出两种材料，不需要联网或模型 API：

```powershell
python -B tools/codex.py voice export resident --out D:/task/Voice-Resident.txt
python -B tools/codex.py voice export project --out D:/task/ChatGPT-Voice-Companion.md
```

输出文件必须不存在，工具不会覆盖原件或自动修改全局配置。`voice instructions resident` / `voice instructions project` 可只查看内容。仓库内的完整单文件是当前源文件的装配产物，修改源后要重新生成；源技能及其三份参考是行为和材料的编辑入口。

## 组成与挂载

| 材料 | 用途 |
|---|---|
| [RESIDENT.txt](RESIDENT.txt) | 可合并到ChatGPT自定义指令或本机个人指导的短常驻核；不替换原DIGR路由。 |
| [START.txt](START.txt) | 明确选用完整附件并开练的一次入口；不会以裸 DIGR 前缀误触正式执行。 |
| [完整英文单文件](ChatGPT-Voice-Companion.md) | 供无本地读取端上传；由同一份源技能和参考装配。 |
| [完整技能](../.agents/skills/digr-voice-companion/SKILL.md) | 当前交流、救场、创作、事实与话轮的具体行为；按需要读取例子。 |
| [对话例子](../.agents/skills/digr-voice-companion/references/examples.md) | 通过真实英文往返展示行为，不是让用户背的答案。 |
| [宿主说明](../.agents/skills/digr-voice-companion/references/hosts.md) | 区分ChatGPT账号指令、本机AGENTS、本地技能与Voice前台，给出对应装载方式。 |

短核适合驻留，完整内容按需。可发现的技能不等于已用于当前语音；项目文件存在也不等于模型已经读过。安装与实际使用分别确认。

## 从DIGR迁入什么

迁入具体对象、自己的眼光、有内容的替代、对异议的实际处理，以及让材料和回应改变下一步。伙伴需要有信息、兴趣、立场和作品，不能只问问题、夸奖、提限制。

不把N/R/D/V换成同一模型脑内人设，不在普通语音报参数、计时或编造后台议会。有真正可用的原生后端时，可以请它研究缺失事实或做更深入准备；不能把API专用控制标记当作ChatGPT已安装工具，也不因一句求助自动发起付费服务。

## 来源与验证边界

本模块按2026-11-10实际读取的[Voice](https://learn.chatgpt.com/docs/features/voice)、[个性化](https://learn.chatgpt.com/docs/personalize)、[技能](https://learn.chatgpt.com/docs/build-skills)与[GPT-Live提示指南](https://developers.openai.com/api/docs/guides/live-prompting)设计。API指南给出前台简短、后台承担详细工作的思路；迁到ChatGPT时只采用其可用原则，不宣称复制了API后端。

真实语音的识别、打断、音频时延与前台加载仍需在实际账号观察；文字演练不能替代该验证。当前设施不承诺提高模型底层能力或自动获得未配置的工具。
