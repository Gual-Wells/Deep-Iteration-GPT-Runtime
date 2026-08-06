# GitHub Deployment

1. 上传完整仓库。
2. 保持根目录存在 `manifest.json`。
3. 建立 `stable` 分支或发布 `v2.0.0` tag。
4. 将本地个性化中的占位地址替换为：

```text
https://raw.githubusercontent.com/<OWNER>/<REPO>/stable/manifest.json
```

固定版本可使用：

```text
https://raw.githubusercontent.com/<OWNER>/<REPO>/v2.0.0/manifest.json
```

建议：

- `main`：开发；
- `stable`：最新稳定；
- release tag：固定审计版本。
