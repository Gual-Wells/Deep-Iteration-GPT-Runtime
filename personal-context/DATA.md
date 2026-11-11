# 数据与变更契约

`profile.json` schema 1：profile_id/revision/integrity、sources、source_heads、entries、history、receipts。JSON + Git 可版本化；不需要服务、数据库或付费 API。writer lock 仅单写者，异常时先核对进程；不得删锁后盲写。

来源 `origin`：user_message、user_material、project_artifact、reference、simulation、learner_observation。内容引用由所选 unit 的规范化文本和 SHA 绑定；命令输出说明提取范围，人工阅读范围写进条目 scope。`CURRENT` 仅表示主要原件字节一致，不能证明其内容今天仍正确。

条目示例（明确合成测试材料，不是实际用户经历）：

```json
{
  "id": "own-contribution",
  "kind": "claim",
  "statement": "材料称自己改过 Android 推理结果的保存逻辑。",
  "scope": "只记录项目文档的个人贡献声明，未验证实现及本人掌握。",
  "as_of": "2026-11-11",
  "sharing": "actor",
  "source_id": "<actual-source-id>",
  "unit_id": "<actual-unit-id>",
  "quote": "<exact-selected-source-quote>"
}
```

kind 可取 goal/preference/fact/claim/self_report/observation/knowledge_evidence/resource/inference/unknown。分类由操作者负责，校验不认证语义。reference/simulation 只能支持 resource/unknown，不能写成人的经历或掌握；knowledge_evidence 要求真实观察或本人原话及 evidence_scope。无 source 的 unknown 要有 reason，不能推导“不会”。

sharing 从最小范围选择 self / scene_author / actor / public。默认 self；作者视图不自动把作者专用信息给演员，演员默认拿不到 self/scene_author 条目。resource 必须显式 `--include-resources`，即使提供也仍叫参考材料。

更正同 ID 要给旧 `replaces_sha256`，历史保留。切换逻辑文档当前版用 source 的 `--lineage ... --current`；移同版用 relocate-source；撤出新使用用 withdraw-source。替换与撤出不是抹除旧出版物。

胶囊包括目的、profile/entry 哈希、条目来源类型、书名、提取范围及引用位置，并绑定 book_id/role_id。check-view 只检查所选项，不因不相关资料变化全部失效。新场景使用前做 live check；一本旧书可保留当时冻结胶囊来解释历史，但不把它叫今天仍有效。

工具没有“替代用户核准”字段，也不把 sources 数量、问题标签或 actors 表现自动变成能力模型。
