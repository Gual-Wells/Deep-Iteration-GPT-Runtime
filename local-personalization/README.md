# ChatGPT Local Personalization

将 `CHATGPT_LOCAL_PERSONALIZATION.txt` 内容粘贴到 ChatGPT Custom Instructions / 个性化指令。

它只负责：触发、远程 manifest 入口、fallback 核心、2.2 输出契约。详细规则仍由 GitHub stable 分支加载。

该文本设计为不超过 Plus 当前 5,000 characters 上限。运行 `tests/validate_repo.py` 会检查字符数。
