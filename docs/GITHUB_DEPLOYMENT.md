# GitHub Deployment

推荐：`main` 开发，`stable` 发布。发布 2.3.0 前运行 `python tests/validate_repo.py` 与 `python -m unittest discover -s tests -v`。

客户端从 stable 启动时：先解析 `refs/heads/stable` 到 commit SHA；本轮 manifest 与模块读取都使用该 SHA。这样 stable 后续移动不会改变进行中的一次 DIGR 运行。
