# DIGR Codex 附属项目

[Paper Pool](../codex/PAPER_POOL.md)是 DIGR Codex 2.0 的唯一附属。它根据研究问题检索论文池，返回可回查的摘要、解释及其来源。摘要证据的适用范围以实际取得的材料为准。

在仓库根目录或同版分发目录运行以下命令，查看论文池的操作入口。

```text
python -B tools/codex.py paper-pool --help
```

正式任务通过 [DIGR Codex](../codex/HELP.md) 进入。Main 为正式学术任务安排独立的 Paper Pool 工作，由当前候选处理返回的成果。根 stable 有自己的[清单](../manifest.json)和[启动协议](../entry/STARTUP.md)。

## 历史任务恢复

DIGRP、Voice Companion、Paper Knowledge、English-Spoken-Preprint 和 Personal Context 在 2.0 退役。历史任务按记录中的 `P_run=版本@完整 SHA` 找回相应分发，使用原版本的工具与原数据绑定。对应项目的说明、命令和技能可从相同 Git SHA 的源树取回。[1.9.0 附属目录归档](https://github.com/Gual-Wells/Deep-Iteration-GPT-Runtime/blob/7223b4722739a63b6cff37163a6ea6b0f2c04854/addons/README.md)
