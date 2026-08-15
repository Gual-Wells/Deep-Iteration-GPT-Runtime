# Architecture

DIGR 2.2 的控制面由 GitHub 文本规则组成，执行面仍是当前 ChatGPT 会话本身。

```text
Invocation
  ↓
U0 anchor
  ↓
Budget parser (N/T)
  ↓
Prompt loop P0…P*
  ↓
Resource gate + workflow design
  ↓
Native execution
  ↓
Result re-entry ── structural failure ──> redo native execution
  ↓
Final response ablation
  ↓
Final result + public runtime report
```

运行记录只公开可安全观察的元数据，不试图输出隐藏思维链。
