# Extension Guide

## 新增模块

### 缺陷消融

在 `ablation/` 新建单一职责 YAML，包含：

```yaml
id: unique-id
objective: "消融目标"
rules:
  - "可执行规则"
```

### 提示优化

在 `optimization/` 新建 YAML。不得仅增加形式复杂度。

### 工作流

在 `workflow/` 新建 YAML。说明激活条件、来源或工具策略、停止条件。

### 验证

在 `validation/` 新建 YAML。检查项应能发现可修复的问题。

## 路由

在 `routing/module-router.yaml` 中添加信号与模块，但路由不得成为原生能力上限。

## 版本

- 规则修订：补丁版本；
- 兼容模块扩充：次版本；
- 触发、状态、阶段或核心语义不兼容：主版本或新协议；
- 更新 `VERSION`、`manifest.json`、`CHANGELOG.md`、Schema 和测试。

## 新规则要求

- 单一职责；
- 最小必要；
- 不覆盖 `U0`；
- 不限制原生能力；
- 附正反例或回归测试；
- 不把模型偏好伪装成用户事实。

## 执行证据扩展

新增证据类型时必须：

- 能映射到真实动作或产物；
- 指明属于外部可核验、运行时自证或未独立证实；
- 更新 `schemas/execution-evidence.schema.json`；
- 增加反伪证据测试；
- 不要求公开隐藏推理。

