# Router candidate matching

The local router performs broad, deterministic, version-semantic-free capture after removing leading whitespace only:

- `DIGR：任务` → route attempt;
- `DIGR/help` → route attempt;
- `  深度迭代（R=5）：任务` → route attempt;
- `DIGR 的设计是不是有问题？` → route attempt; the pinned repository may return `NATIVE`;
- `digr：任务` / `Digr/help` → no DIGR route attempt;
- `我觉得 DIGR 的设计有问题` → no route attempt because the key is not at message head.

The local layer does not decide task/help/native/invalid, parse parameters or inspect punctuation after the key. Repository startup classification owns that boundary.
