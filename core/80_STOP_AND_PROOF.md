# 80 — Stop Gates & Minimal Proof

正常结束前至少确认：
- 主体 N minimum 已满足（若用户指定）；
- 主体 R minimum 已满足（若用户指定）；
- 每个实际 S 的 n/r minimum 已满足；
- B=hard 时可信 total elapsed >= T；
- b=hard 时可信 aggregate source elapsed >= t；
- 当前不存在仍明显值得处理、足以实质提高 U0 核心结果的重大质量缺口。

soft T/t 在充分收敛时可以提前结束。

Hard 时间未满足时，继续由 ChatGPT 原生判断如何进化；不可用等待、重复、伪搜索、伪树节点、机械改写或输出膨胀填充。

资源/平台/安全/权限等真实限制导致 hard 约束不可验证或不可满足时，交付最佳可用结果，但 proof 必须明确 `✗/unverified/resource-limited`，不得伪称满足。

默认先完整交付真正任务结果，最后只附一条轻量证明：
```text
【DIGR 3.0｜N 3→5｜T 15mH→16m08s✓｜R 2→3｜S×4〔n≥2 · S-time 6mH→7m21s · r≥1〕✓】
```

默认不返回 final P*、EST、每轮过程、自评分、workflow chain、查询/来源日志副本或 protocol SHA。任务正文自身需要的引用、来源、工具结果、测试与证据应正常呈现在正文。
