# GitHub Deployment

建议先在分支导入本包并运行：

```bash
python tests/validate_repo.py
python -m unittest tests.test_reference_parser
```

通过后再将目标分支更新为本版本。若 `stable` 用作远程运行入口，应确保 `stable/manifest.json` 与本包版本一致，再更新本地 ChatGPT 个性化指令。
