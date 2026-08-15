# 20 — Module Routing

读取 `routing/module-router.yaml`，先加载 defaults，再按 U0 的任务类型添加最少必要模块。

路由只影响 DIGR 的显式检查模块，不限制 ChatGPT 原生能力。若执行中出现新证据、新任务类型或工具失败，可动态增删模块。

复杂度预算 T 影响模块深度而非简单按数量堆模块；高 T 优先增加有独立信息增益的验证路径。
