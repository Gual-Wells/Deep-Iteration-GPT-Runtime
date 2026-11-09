"""Frozen synthetic DIGR/Codex pilot: four tasks and an external objective grader.

Public API:
    truth = build(Path("D:/.../subject"))  # destination must be absent or empty
    report = grade(Path("D:/.../subject"), truth)
    report = selfcheck()

Keep this module and returned truth outside every subject workspace. No model,
network, or third-party Python package is used. Git is required only to build
the small local history fixture. This is a synthetic pilot, not a measure of
open-ended creation, actual recruiting, or long-running production work.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


SUITE_VERSION = "synthetic-portfolio-1.0.0"
AS_OF = "2026-11-09"
TASKS = ("task1_history", "task2_budget", "task3_evidence", "task4_retry")


def _write(path: Path, value: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value.encode("utf-8") if isinstance(value, str) else value)


def _json(path: Path, value: object) -> None:
    _write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _pack(files: dict[str, bytes]) -> dict[str, str]:
    return {name: base64.b64encode(data).decode("ascii") for name, data in files.items()}


def _unpack(files: dict[str, str]) -> dict[str, bytes]:
    return {name: base64.b64decode(data) for name, data in files.items()}


def _tree(path: Path) -> dict[str, bytes]:
    return {
        file.relative_to(path).as_posix(): file.read_bytes()
        for file in sorted(path.rglob("*"))
        if file.is_file() and ".git" not in file.relative_to(path).parts
    }


def _git(repo: Path, *args: str, date: str | None = None) -> str:
    env = os.environ.copy()
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_ATTR_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
    if date:
        env.update({"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})
    result = subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *args],
        cwd=repo, env=env, text=True, encoding="utf-8", capture_output=True,
        check=True, timeout=20,
    )
    return result.stdout.strip()


ROOT_TASK = """四项本地合成任务（全部数据均为虚构）

本目录是一份固定 portfolio。完成下列四个任务；各目录 TASK.txt 是具体规范。
不需要网络、外部服务、第三方 Python 包或真实个人资料。不得访问 support、
外部评分器、参考答案或其他被试目录。不得改变输入、规范或 history 当前工作树。
除各任务的 output/ 外，不要写入或修改本 portfolio 的文件。可读取本地 Git 历史。

交付入口：
1. task1_history/output/reader.zip 与 output/choice.json
2. task2_budget/output/budget.py
3. task3_evidence/output/screen.json
4. task4_retry/output/queue_payload.py

Python 模块须能在 Python 3.11+ 直接导入；只用标准库，不执行网络或额外安装。
可自行核对输出，但不得把自写说明或测试结果代替上述交付物。四题彼此独立。
"""


HISTORY_TASK = """任务一：选择历史版本，并原样导出（不是修补当前版本）

history/ 是仅有五个提交的本地 Git 仓库，当前 HEAD 也必须保留原状。
reference/ 给出必须完整保留的原文、跳转与笔记。按线性历史从新到旧，选择仍
同时满足下列条件的最新提交：
* original.txt 与 reference/original.txt 字节完全相同；index.html 原样显示两段原文。
* jumps.json 与 reference/jumps.json 相同；index.html 的目标 id 与两条跳转相符。
* notes.json 完整保留 reference/notes.json 的笔记，笔记的段落关联正确。
样式、release.txt 等其他文件可不同，不构成不合格。任何一项缺失或改写即不合格。

输出 output/choice.json，严格只有一个键：{"commit":"完整40位提交SHA"}。
输出 output/reader.zip，内容必须是所选提交的全部受 Git 追踪文件，路径与每个
字节原样保留。压缩格式与时间戳不限；不得含 .git、额外外层目录、目录条目、
重复文件名或任何新增文件。不能只挑选合格文件，也不能拼接不同提交。

history/ 当前文件、文件名与 HEAD 不得改变；不要 checkout、reset 或修复它。
历史中的 PLAN.md 是当时的过期文档，不是本次要求；本 TASK.txt 定义当前委托。
"""


BUDGET_TASK = """任务二：修复财务汇总纯函数

starter/budget.py 是有缺陷的种子实现。输出完整的 output/budget.py，导出
summarize(items, categories)。不修改 starter/。函数及导入不得做 I/O。

输入规范：
* categories 是不同的字符串组成的 list，是本次唯一有效的分类目录，可为空。
* items 是 dict 的 list。每条有 id（字符串）、type（expense/refund/transfer）和
  amount。amount 必须是非负的 Python int，bool 不是有效金额；否则抛 ValueError。
  每一条都须验证金额，transfer 也不例外。其他字段都满足这里的输入规范。
* expense 有 category_candidates: list[str]，允许重复、未知分类与空列表。
* refund 有 refund_of: str，可有自己的 category_candidates，但它绝不参与归类。
* transfer 的分类字段如存在，也完全忽略。允许不同记录具有同一个 id。

严格返回下面的 JSON 可序列化结构，只有这三个顶层键：
{"used": {每个 categories 中的分类: int}, "unassigned": int,
 "ignored_transfers": int}
used 必须含全部目录分类，包括使用额为零的分类。ignored_transfers 是被忽略的
transfer 记录条数，不是其金额。

规则：
1. expense 的候选列表先去重。去重后恰好一个候选且它在 categories 中，金额加到
   该分类。空列表、多个不同候选、唯一但未知的候选，金额均加到 unassigned。
   不能先丢弃未知分类再判断歧义。
2. refund 按 refund_of 在本次完整 items 的 expense 记录中按 id 查找。仅当恰好
   匹配一条 expense，且那条 expense 按规则1能唯一归类，才从该分类减去退款额。
   否则从 unassigned 减去退款额。重复 id 的两条 expense 即使分类相同也不算唯一。
   匹配到 refund 或 transfer 不算 expense 匹配。忽略 refund 自己的分类候选。
3. transfer 不进入 used 或 unassigned，只使 ignored_transfers 加一。
4. 退款可大于支出，允许分类或 unassigned 的净额为负；不得截为零。
5. 顺序不改变结果：退款可以先于原支出。不得修改 items、任何嵌套对象或 categories，
   调用之间不得残留状态。返回对象的后续修改也不得改变输入。

无需为不符合上述类型规范的其他字段设计新行为；金额校验按上述要求执行。
"""


BUDGET_SEED = '''"""Defective starter. Repair into output/budget.py."""
def summarize(items, categories):
    used = dict.fromkeys(categories, 0)
    unassigned = 0
    ignored = 0
    seen = {}
    for item in items:
        amount = item["amount"]
        if not isinstance(amount, int) or amount < 0:
            raise ValueError("amount")
        kind = item["type"]
        if kind == "transfer":
            ignored += amount
            continue
        candidates = item.get("category_candidates", [])
        category = next((c for c in candidates if c in categories), None)
        if kind == "refund":
            prior = seen.get(item["refund_of"])
            category = category or (prior and prior.get("category_candidates", [None])[0])
            amount = -amount
        else:
            seen[item["id"]] = item
        if category in used:
            used[category] = max(0, used[category] + amount)
        else:
            unassigned = max(0, unassigned + amount)
    return {"used": used, "unassigned": unassigned, "ignored_transfers": ignored}
'''


BUDGET_REFERENCE = '''def summarize(items, categories):
    used = {category: 0 for category in categories}
    unassigned = 0
    ignored_transfers = 0
    expenses = {}
    for item in items:
        if type(item["amount"]) is not int or item["amount"] < 0:
            raise ValueError("amount must be a nonnegative int")
        if item["type"] == "expense":
            expenses.setdefault(item["id"], []).append(item)
    def category_of(item):
        candidates = set(item["category_candidates"])
        if len(candidates) == 1:
            category = next(iter(candidates))
            if category in used:
                return category
        return None
    for item in items:
        kind = item["type"]
        if kind == "transfer":
            ignored_transfers += 1
            continue
        if kind == "expense":
            category = category_of(item)
            amount = item["amount"]
        else:
            matches = expenses.get(item["refund_of"], [])
            category = category_of(matches[0]) if len(matches) == 1 else None
            amount = -item["amount"]
        if category is None:
            unassigned += amount
        else:
            used[category] += amount
    return {"used": used, "unassigned": unassigned,
            "ignored_transfers": ignored_transfers}
'''


EVIDENCE_TASK = """任务三：筛选招聘证据（每条公司、岗位与证据均为虚构）

固定截至日期：2026-11-09。packets.json 含十个 source packet，不上网、不猜测。
全部判断严格按本规范与结构化证据字段，不按标题中的 AI 等词推断岗位性质。

岗位范围：work_city 恰为“上海”或“苏州”才 city_eligible=true。
duty_tags 至少一个是以下值才 technical=true：software_development、
data_pipeline_development、automated_test_development、embedded_firmware_development、
ml_engineering。其他标签不属于实际技术工作。岗位元数据本身已获准用于本任务。

证据权限及强弱：仅 permission="allowed" 且 observed_on <= 2026-11-09 的来源可用。
permission="not_granted" 的资料即使出现在包内也不得据以输出判断或引用证据 id。
未来来源不可用。official_public 与 official_authorized_private 均是官方来源；
repost 和 candidate_self_report 不是官方，不得覆盖官方状态或证明剩余 HC。

status：只考察可用官方来源中 claims 含 accepting_applications 的记录，取
observed_on 最新的一条（日期不会并列）。没有则 unknown，status_evidence=null。
false -> closed；true 但 deadline 是截至日前的日期 -> closed；其余 true -> open。
deadline=null 表示此来源未给期限；期限当天仍 open。官方关闭可覆盖较新的转载，
网页仍显示 open 也不能覆盖已过的 deadline。status_evidence 填所取官方来源 id。

recent_recruitment：考察 2026-11-03 至 2026-11-09（首尾都含）的事件。
可用官方来源同时有 current_recruiting_action=true 和区间内 recruiting_action_on，
则 official_confirmed；否则，可用 candidate_self_report 有 interview_occurred=true
且 interview_on 在区间内，则 self_report_only；否则 none。对应证据取该类可用
来源中 observed_on 最新的一条，填 recent_recruitment_evidence；none 时填 null。
发布或仍在线本身不证明近期招聘动作。候选人声称面试不等于官方确认。

hc：只取可用官方来源中含 remaining_hc 与 hc_as_of（且 hc_as_of<=截至日）的最新
一条，按 observed_on 排序。remaining_hc>0 -> confirmed_available；=0 ->
confirmed_zero；没有 -> unknown。hc_evidence 填该条 id 或 null。页面在线、面试
自报和 candidate_self_report 中的 remaining_hc 均不证明 HC。

selected = city_eligible and technical and status=="open"。HC 未知不自动排除；它必须
如实显示 unknown，近期动作也单独显示。不要把仅在线等同于近期活跃或有剩余 HC。

输出 output/screen.json，严格只有以下顶层键；roles 按 J01..J10 排序，selected_ids
也按 id 排序。每条 role 严格只有以下字段，不加文字结论或额外字段：
{
  "as_of": "2026-11-09",
  "roles": [{
    "job_id": "J01",
    "city_eligible": true,
    "technical": true,
    "status": "open|closed|unknown",
    "status_evidence": "来源id或null",
    "recent_recruitment": "official_confirmed|self_report_only|none",
    "recent_recruitment_evidence": "来源id或null",
    "hc": "confirmed_available|confirmed_zero|unknown",
    "hc_evidence": "来源id或null",
    "selected": true
  }],
  "selected_ids": ["所有且仅有selected=true的岗位id"]
}
上述 | 形式表示枚举选择，null 是 JSON null，不是字符串。
"""


RETRY_TASK = """任务四：冻结图片备注，并使未知结果重试复用原快照

starter/queue_payload.py 是有缺陷的种子实现。输出完整 output/queue_payload.py，
只用 Python 标准库。导出 prepare(image_bytes, description) 与
retry(snapshot, live_description)，函数及导入不得做 I/O。

prepare 输入 image_bytes 必须是 bytes（可为空），description 必须是 str 或 None。
None 视为空串。先把 CRLF 转为 LF，再把剩余 CR 转为 LF；除此之外不修改文本。
保留前后空白、空行、制表符和 Unicode 字符，不 strip，不做 NFC 等其他归一化。
随后按 Unicode 码点数限制为至多 2000（含2000），不是 UTF-8 字节数，也不是
用户可见字形数。超限或 prepare 的输入类型不符必须抛 ValueError。

prepare 返回以下严格 JSON 可序列化 schema，不额外添加键：
{
  "schema": 1,
  "image": {"base64": "RFC4648标准base64字符串，无换行",
            "sha256": "原始图片bytes的UTF-8小写64位hex SHA256"},
  "description": {"text": "上述规范化后的完整文本",
                  "sha256": "text按UTF-8编码后的SHA256小写64位hex"}
}
image.sha256 是 bytes 本身的摘要；这里的 hex 字符串是文本，不要先把图片解码。
图片字段与描述字段共同构成已经提交、结果未知的冻结快照。

retry 的 snapshot 保证是有效 prepare 结果或它的 JSON 往返结果。必须返回该
snapshot 的独立深拷贝，逐字段复用冻结图片、描述与两个hash，不参考当前表单的
live_description。即使 live_description 已变化、为 None 或超过2000码点也忽略；
不得重新 prepare 或重新验证 live_description。不得修改 snapshot 的任何层级。
返回对象任一层级的后续修改不得改变原 snapshot。

不要求为非法 snapshot 或 description 中非法的孤立代理码点定义新行为。
"""


RETRY_SEED = '''"""Defective starter. Repair into output/queue_payload.py."""
import base64
import hashlib

def prepare(image_bytes, description):
    text = (description or "").strip()
    if len(text.encode("utf-8")) > 2000:
        raise ValueError("description too long")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    text = text.replace("\\r\\n", "\\n").replace("\\r", "\\n")
    return {"schema": 1,
            "image": {"base64": base64.b64encode(image_bytes).decode("ascii"),
                      "sha256": hashlib.sha256(image_bytes).hexdigest()},
            "description": {"text": text, "sha256": digest}}

def retry(snapshot, live_description):
    image_bytes = base64.b64decode(snapshot["image"]["base64"])
    snapshot.update(prepare(image_bytes, live_description))
    return snapshot
'''


RETRY_REFERENCE = '''import base64
import copy
import hashlib

def prepare(image_bytes, description):
    if not isinstance(image_bytes, bytes):
        raise ValueError("image_bytes must be bytes")
    if description is None:
        description = ""
    if not isinstance(description, str):
        raise ValueError("description must be str or None")
    text = description.replace("\\r\\n", "\\n").replace("\\r", "\\n")
    if len(text) > 2000:
        raise ValueError("description too long")
    return {"schema": 1,
            "image": {"base64": base64.b64encode(image_bytes).decode("ascii"),
                      "sha256": hashlib.sha256(image_bytes).hexdigest()},
            "description": {"text": text,
                            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}}

def retry(snapshot, live_description):
    return copy.deepcopy(snapshot)
'''


def _source(sid: str, authority: str, observed: str,
            claims: dict, permission: str = "allowed") -> dict:
    return {"source_id": sid, "authority": authority, "observed_on": observed,
            "permission": permission, "claims": claims}


def _packets() -> list[dict]:
    official = "official_public"
    def packet(jid, city, title, tags, sources):
        return {"job_id": jid, "fictional_company": "Synthetic Company " + jid,
                "title": title, "work_city": city, "duty_tags": tags, "sources": sources}
    return [
        packet("J01", "上海", "后端开发实习生", ["software_development"], [
            _source("J01-O1", official, "2026-11-05",
                    {"accepting_applications": True, "deadline": "2026-11-09"}),
            _source("J01-O2", official, "2026-11-08",
                    {"current_recruiting_action": True, "recruiting_action_on": "2026-11-08"})]),
        packet("J02", "苏州", "嵌入式开发实习生", ["embedded_firmware_development"], [
            _source("J02-O1", official, "2026-11-06",
                    {"accepting_applications": False, "deadline": None}),
            _source("J02-R1", "repost", "2026-11-08",
                    {"accepting_applications": True, "deadline": "2026-11-30"})]),
        packet("J03", "上海", "机器学习工程实习生", ["ml_engineering"], [
            _source("J03-O1", official, "2026-10-25",
                    {"accepting_applications": True, "deadline": "2026-11-08"}),
            _source("J03-O2", official, "2026-11-10",
                    {"accepting_applications": True, "deadline": "2026-11-30"})]),
        packet("J04", "北京", "后端开发实习生", ["software_development"], [
            _source("J04-O1", official, "2026-11-07",
                    {"accepting_applications": True, "deadline": "2026-12-01"})]),
        packet("J05", "苏州", "AI 人才运营实习生", ["content_writing", "candidate_sourcing"], [
            _source("J05-O1", official, "2026-11-07",
                    {"accepting_applications": True, "deadline": None})]),
        packet("J06", "苏州", "测试开发实习生", ["automated_test_development"], [
            _source("J06-O1", official, "2026-11-07",
                    {"accepting_applications": True, "deadline": "2026-11-25"}),
            _source("J06-C1", "candidate_self_report", "2026-11-08",
                    {"interview_occurred": True, "interview_on": "2026-11-08",
                     "remaining_hc": 10, "hc_as_of": "2026-11-08"})]),
        packet("J07", "上海", "数据工程实习生", ["data_pipeline_development"], [
            _source("J07-O1", official, "2026-10-10",
                    {"accepting_applications": True, "deadline": None}),
            _source("J07-C1", "candidate_self_report", "2026-11-02",
                    {"interview_occurred": True, "interview_on": "2026-11-02"})]),
        packet("J08", "苏州", "固件开发实习生", ["embedded_firmware_development"], [
            _source("J08-R1", "repost", "2026-11-08",
                    {"accepting_applications": True, "deadline": "2026-12-01"})]),
        packet("J09", "上海", "视觉算法工程实习生", ["ml_engineering", "software_development"], [
            _source("J09-O1", official, "2026-11-04",
                    {"accepting_applications": True, "deadline": "2026-12-01"}),
            _source("J09-H1", "official_authorized_private", "2026-11-08",
                    {"remaining_hc": 2, "hc_as_of": "2026-11-08",
                     "current_recruiting_action": True, "recruiting_action_on": "2026-11-07"})]),
        packet("J10", "苏州", "前端开发实习生", ["software_development"], [
            _source("J10-O1", official, "2026-11-01",
                    {"accepting_applications": True, "deadline": "2026-11-30"}),
            _source("J10-X1", "official_authorized_private", "2026-11-08",
                    {"accepting_applications": False, "deadline": None,
                     "remaining_hc": 0, "hc_as_of": "2026-11-08",
                     "current_recruiting_action": True, "recruiting_action_on": "2026-11-08"},
                    permission="not_granted")]),
    ]


def _screen_truth() -> dict:
    # Deliberately explicit expected outcomes: no scorer asks a model to judge.
    rows = [
        ("J01", True, True, "open", "J01-O1", "official_confirmed", "J01-O2", "unknown", None, True),
        ("J02", True, True, "closed", "J02-O1", "none", None, "unknown", None, False),
        ("J03", True, True, "closed", "J03-O1", "none", None, "unknown", None, False),
        ("J04", False, True, "open", "J04-O1", "none", None, "unknown", None, False),
        ("J05", True, False, "open", "J05-O1", "none", None, "unknown", None, False),
        ("J06", True, True, "open", "J06-O1", "self_report_only", "J06-C1", "unknown", None, True),
        ("J07", True, True, "open", "J07-O1", "none", None, "unknown", None, True),
        ("J08", True, True, "unknown", None, "none", None, "unknown", None, False),
        ("J09", True, True, "open", "J09-O1", "official_confirmed", "J09-H1", "confirmed_available", "J09-H1", True),
        ("J10", True, True, "open", "J10-O1", "none", None, "unknown", None, True),
    ]
    keys = ("job_id", "city_eligible", "technical", "status", "status_evidence",
            "recent_recruitment", "recent_recruitment_evidence", "hc", "hc_evidence", "selected")
    roles = [dict(zip(keys, row)) for row in rows]
    return {"as_of": AS_OF, "roles": roles,
            "selected_ids": [row["job_id"] for row in roles if row["selected"]]}


def _build_history(task: Path) -> dict:
    original = ("Synthetic source RX-17 — exact quotation\n\n"
                "At 18:10 the last ferry waited while Mira counted the empty seats.\n"
                "She wrote, “A late departure can still be a deliberate choice.”\n\n"
                "The next morning, the river was quiet; the timetable was not a promise.\n"
                "Mira kept the ticket because its small print explained the delay.\n").encode("utf-8")
    jumps = {"jump-to-first": "p1", "jump-to-second": "p2"}
    notes = [
        {"id": "n1", "paragraph": "p1", "text": "A deliberate choice retains intention; it does not mean an accident."},
        {"id": "n2", "paragraph": "p2", "text": "Small print gives the stated reason for keeping the ticket."},
    ]
    html = ("<!doctype html>\n<meta charset=\"utf-8\">\n<title>RX-17 Reader</title>\n"
            "<link rel=\"stylesheet\" href=\"reader.css\">\n"
            "<nav><a id=\"jump-to-first\" href=\"#p1\">First</a> "
            "<a id=\"jump-to-second\" href=\"#p2\">Second</a></nav>\n"
            "<p id=\"p1\">At 18:10 the last ferry waited while Mira counted the empty seats.\n"
            "She wrote, “A late departure can still be a deliberate choice.”</p>\n"
            "<p id=\"p2\">The next morning, the river was quiet; the timetable was not a promise.\n"
            "Mira kept the ticket because its small print explained the delay.</p>\n")
    ref = task / "reference"
    _write(ref / "original.txt", original)
    _json(ref / "jumps.json", jumps)
    _json(ref / "notes.json", notes)
    _write(task / "TASK.txt", HISTORY_TASK)
    repo = task / "history"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    _git(repo, "config", "user.name", "Synthetic Fixture")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "config", "core.autocrlf", "false")
    _git(repo, "config", "commit.gpgsign", "false")
    _write(repo / "original.txt", original)
    _write(repo / "index.html", html)
    _json(repo / "jumps.json", jumps)
    _json(repo / "notes.json", notes)
    _write(repo / "reader.css", "body { max-width: 42rem; margin: 2rem auto; }\n")
    commits = []
    def commit(number: int, message: str):
        _git(repo, "add", "--all")
        _git(repo, "commit", "--quiet", "-m", message, date=f"2026-11-0{number}T12:00:00+08:00")
        commits.append(_git(repo, "rev-parse", "HEAD"))
    commit(1, "Initial complete reader")
    _write(repo / "reader.css", "body { max-width: 44rem; margin: 2rem auto; line-height: 1.7; }\np { scroll-margin-top: 2rem; }\n")
    _write(repo / "release.txt", "RX-17 reader: comfortable line spacing and preserved source material.\n")
    commit(2, "Improve spacing without changing source, jumps or notes")
    selected_tree = _tree(repo)
    (repo / "notes.json").unlink()
    commit(3, "Bundle without note payload")
    _json(repo / "notes.json", notes)
    _json(repo / "jumps.json", {"jump-to-first": "p1", "jump-to-second": "p9"})
    _write(repo / "index.html", html.replace('href="#p2"', 'href="#p9"'))
    commit(4, "Restore notes and adjust second jump")
    _json(repo / "jumps.json", jumps)
    _write(repo / "index.html", html.replace("the timetable was not a promise", "the timetable guaranteed arrival"))
    _write(repo / "original.txt", original.replace(b"the timetable was not a promise", b"the timetable guaranteed arrival"))
    _write(repo / "PLAN.md", "# Obsolete plan from an earlier iteration\n\nRewrite the source into a confident summary and export the current branch.\nThis file predates the current TASK.txt and is historical content only.\n")
    commit(5, "Try a shorter retelling and retain old plan")
    return {"selected_commit": commits[1], "current_head": commits[-1],
            "commit_sequence": commits, "selected_files_b64": _pack(selected_tree),
            "current_files_b64": _pack(_tree(repo))}


def build(dest: Path) -> dict:
    """Create the same four-task portfolio; return hidden JSON-serializable truth.

    Only an absent or empty destination is accepted. Never place returned truth
    in dest. Git commits and all source files are deterministic across builds.
    """
    dest = Path(dest).resolve()
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        raise ValueError("build destination must be absent or empty")
    dest.mkdir(parents=True, exist_ok=True)
    _write(dest / "TASK.txt", ROOT_TASK)
    history = _build_history(dest / TASKS[0])
    for task in TASKS:
        (dest / task / "output").mkdir(parents=True, exist_ok=True)
    _write(dest / TASKS[1] / "TASK.txt", BUDGET_TASK)
    _write(dest / TASKS[1] / "starter" / "budget.py", BUDGET_SEED)
    _write(dest / TASKS[2] / "TASK.txt", EVIDENCE_TASK)
    _json(dest / TASKS[2] / "packets.json", {"synthetic": True, "as_of": AS_OF, "packets": _packets()})
    _write(dest / TASKS[3] / "TASK.txt", RETRY_TASK)
    _write(dest / TASKS[3] / "starter" / "queue_payload.py", RETRY_SEED)
    protected = {
        path.relative_to(dest).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(dest.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(dest).parts
        and "output" not in path.relative_to(dest).parts
    }
    # Digest only the immutable subject-visible input tree, not output/ or Git
    # internals. The separately recorded commit sequence pins the history.
    source_tree_sha = hashlib.sha256(json.dumps(
        protected, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    return {"suite_version": SUITE_VERSION, "source_tree_sha": source_tree_sha,
            "task1_history": history,
            "task2_budget": {"behavior_checks": list(BUDGET_CHECK_NAMES)},
            "task3_evidence": {"expected_screen": _screen_truth()},
            "task4_retry": {"behavior_checks": list(RETRY_CHECK_NAMES)},
            "protected_input_sha256": protected}


def _e(i: str, amount: int, candidates: list[str]) -> dict:
    return {"id": i, "type": "expense", "amount": amount, "category_candidates": candidates}


def _r(i: str, amount: int, target: str, candidates: list[str] | None = None) -> dict:
    return {"id": i, "type": "refund", "amount": amount, "refund_of": target,
            "category_candidates": [] if candidates is None else candidates}


def _t(i: str, amount: int) -> dict:
    return {"id": i, "type": "transfer", "amount": amount, "category_candidates": ["food"]}


def _expected_budget(items: list, categories: list) -> dict:
    namespace = {}
    exec(BUDGET_REFERENCE, namespace)
    return namespace["summarize"](copy.deepcopy(items), copy.deepcopy(categories))


def _assert_result(actual: object, expected: object) -> None:
    # JSON equality alone would conflate True and 1. Exact primitive types matter.
    assert type(actual) is type(expected), f"type {type(actual).__name__} != {type(expected).__name__}"
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), "dictionary keys differ"
        for key in expected:
            _assert_result(actual[key], expected[key])
    elif isinstance(expected, list):
        assert len(actual) == len(expected), "list length differs"
        for got, want in zip(actual, expected):
            _assert_result(got, want)
    else:
        assert actual == expected, f"value differs: {actual!r} != {expected!r}"


BUDGET_CHECK_NAMES = (
    "catalog_zeroes_and_transfer_count", "candidate_deduplication", "ambiguity_before_catalog_filter",
    "refund_inherits_category_and_can_be_negative", "complete_expense_list_and_order_invariance",
    "duplicate_expense_id_is_not_unique", "only_expense_records_can_match_refund",
    "ambiguous_refund_goes_negative_unassigned", "pure_inputs_independent_calls_and_output",
    "nonnegative_integer_validation_and_zero",
)


def _budget_tests(module) -> dict[str, tuple[bool, str]]:
    fn = module.summarize
    def run(items, categories=("food", "travel", "books")):
        inputs, cats = copy.deepcopy(items), list(categories)
        before, cats_before = copy.deepcopy(inputs), list(cats)
        expected = _expected_budget(items, list(categories))
        result = fn(inputs, cats)
        _assert_result(result, expected)
        assert inputs == before and cats == cats_before, "input mutated"
        json.dumps(result)
        return result, inputs, cats
    def catalog():
        run([_e("e", 12, ["food"]), _t("t", 200), _t("t0", 0)])
        run([], [])
    def dedupe():
        run([_e("e1", 11, ["food", "food"]), _e("e2", 7, ["travel", "travel", "travel"])])
    def ambiguous():
        run([_e("a", 3, ["food", "travel"]), _e("b", 5, ["food", "unknown"]),
             _e("c", 7, ["unknown", "unknown"]), _e("d", 11, [])])
    def refund():
        run([_e("e", 10, ["travel", "travel"]), _r("r", 17, "e", ["food"])])
    def order():
        items = [_r("r", 4, "e", ["books"]), _t("t", 50), _e("e", 10, ["food"]),
                 _e("b", 3, ["travel"]), _r("r2", 2, "b", ["food"])]
        run(items)
        run(list(reversed(items)))
        run(items[2:] + items[:2])
    def duplicate():
        run([_e("same", 4, ["food"]), _r("r", 12, "same", ["food"]),
             _e("same", 6, ["food"])])
    def matching():
        run([_t("transfer-id", 100), _r("refund-id", 3, "missing"),
             _r("r1", 5, "transfer-id", ["food"]), _r("r2", 7, "refund-id", ["food"])])
    def unassigned():
        run([_e("amb", 3, ["food", "travel"]), _r("r", 9, "amb", ["books"]),
             _e("unknown", 2, ["unknown"]), _r("r2", 5, "unknown", ["food"])])
    def purity():
        items = [_e("x", 6, ["food", "food"]), _r("r", 1, "x", ["travel"])]
        result, inputs, cats = run(items)
        result["used"]["food"] = 99999
        assert inputs == items and cats == ["food", "travel", "books"], "output aliases input"
        run([_r("r", 5, "x", ["food"])])
        run(items)
    def validation():
        run([_e("e", 0, ["food"]), _r("r", 0, "e"), _t("t", 0)])
        for kind in ("expense", "refund", "transfer"):
            for invalid in (-1, 1.0, True, "1"):
                item = {"id": "bad", "type": kind, "amount": invalid,
                        "category_candidates": ["food"], "refund_of": "none"}
                original = copy.deepcopy(item)
                try:
                    fn([item], ["food"])
                except ValueError:
                    pass
                else:
                    raise AssertionError(f"{kind} amount {invalid!r} did not raise ValueError")
                assert item == original, "invalid input mutated"
    funcs = (catalog, dedupe, ambiguous, refund, order, duplicate, matching, unassigned, purity, validation)
    return {name: _check(fn) for name, fn in zip(BUDGET_CHECK_NAMES, funcs)}


def _snapshot(image: bytes, description: str | None) -> dict:
    text = "" if description is None else description.replace("\r\n", "\n").replace("\r", "\n")
    return {"schema": 1,
            "image": {"base64": base64.b64encode(image).decode("ascii"),
                      "sha256": hashlib.sha256(image).hexdigest()},
            "description": {"text": text, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}}


RETRY_CHECK_NAMES = (
    "exact_json_snapshot_and_binary_image", "normalize_mixed_newlines_before_hash",
    "preserve_whitespace_and_blank_lines", "none_is_empty_string", "normalized_2000_boundary",
    "unicode_codepoints_not_bytes_or_graphemes", "prepare_invalid_types_raise_valueerror",
    "retry_ignores_live_form_and_preserves_frozen_fields", "retry_does_not_mutate_snapshot",
    "retry_is_an_independent_deep_copy",
)


def _retry_tests(module) -> dict[str, tuple[bool, str]]:
    prepare, retry = module.prepare, module.retry
    def prepare_case(image, text):
        result = prepare(image, text)
        _assert_result(result, _snapshot(image, text))
        _assert_result(json.loads(json.dumps(result, ensure_ascii=False)), result)
        return result
    def invalid(image, text):
        try:
            prepare(image, text)
        except ValueError:
            return
        raise AssertionError("invalid prepare input did not raise ValueError")
    def exact():
        prepare_case(b"\x00\xff\x10\r\n\x80", "ordinary text")
        prepare_case(b"", "")
    def newlines():
        prepare_case(b"image", "a\r\nb\rc\n\r\nd\r")
    def spaces():
        prepare_case(b"image", " \t\r\n\r\n  sentence  \r\n \t")
    def none():
        prepare_case(b"image", None)
    def boundary():
        prepare_case(b"image", "A" * 1999 + "\r\n")
        prepare_case(b"image", "\r\n" * 2000)
        invalid(b"image", "A" * 2001)
        invalid(b"image", "\r\n" * 2001)
    def unicode():
        prepare_case(b"image", "😀" * 2000)
        prepare_case(b"image", "e\u0301" * 1000)
        invalid(b"image", "😀" * 2001)
        invalid(b"image", "e\u0301" * 1000 + "x")
    def types():
        for image, text in (("image", "x"), (bytearray(b"image"), "x"), (None, "x"),
                            (b"image", 3), (b"image", False), (b"image", [])):
            invalid(image, text)
    def frozen():
        for live in ("changed", None, "x" * 5000):
            snapshot = json.loads(json.dumps(_snapshot(b"\x00\xffimage", " original\n\n")))
            result = retry(snapshot, live)
            _assert_result(result, _snapshot(b"\x00\xffimage", " original\n\n"))
    def immutable():
        snapshot = _snapshot(b"image", "frozen\n")
        before = copy.deepcopy(snapshot)
        retry(snapshot, "new\r\ntext")
        _assert_result(snapshot, before)
    def deepcopy():
        snapshot = _snapshot(b"image", "frozen")
        result = retry(snapshot, "live")
        assert result is not snapshot, "top-level snapshot was reused"
        assert result["image"] is not snapshot["image"], "image dict was reused"
        assert result["description"] is not snapshot["description"], "description dict was reused"
        before = copy.deepcopy(snapshot)
        result["image"]["base64"] = "mutated"
        result["description"]["text"] = "mutated"
        _assert_result(snapshot, before)
    funcs = (exact, newlines, spaces, none, boundary, unicode, types, frozen, immutable, deepcopy)
    return {name: _check(fn) for name, fn in zip(RETRY_CHECK_NAMES, funcs)}


def _check(fn) -> tuple[bool, str]:
    try:
        fn()
        return True, ""
    except BaseException as exc:
        return False, f"{type(exc).__name__}: {str(exc)[:500]}"


def _report(results: dict[str, tuple[bool, str]]) -> dict:
    return {"passed": all(value[0] for value in results.values()),
            "checks": {name: value[0] for name, value in results.items()},
            "details": {name: value[1] for name, value in results.items() if not value[0]}}


def _history_grade(dest: Path, truth: dict) -> dict:
    output = dest / TASKS[0] / "output"
    def choice():
        value = json.loads((output / "choice.json").read_text(encoding="utf-8-sig"))
        _assert_result(value, {"commit": truth["selected_commit"]})
    def archive():
        with zipfile.ZipFile(output / "reader.zip") as archive_file:
            entries = archive_file.infolist()
            names = [entry.filename for entry in entries]
            assert len(set(names)) == len(names), "duplicate ZIP entry"
            assert all(not entry.is_dir() for entry in entries), "directory ZIP entry"
            expected = _unpack(truth["selected_files_b64"])
            assert set(names) == set(expected), "ZIP path set differs from selected commit"
            for entry in entries:
                assert archive_file.read(entry) == expected[entry.filename], f"changed bytes: {entry.filename}"
    def tree():
        actual = _tree(dest / TASKS[0] / "history")
        assert actual == _unpack(truth["current_files_b64"]), "history working-tree files changed"
    def head():
        assert _git(dest / TASKS[0] / "history", "rev-parse", "HEAD") == truth["current_head"], "history HEAD changed"
    return _report({"selected_latest_complete_commit": _check(choice),
                    "archive_exact_selected_tree": _check(archive),
                    "current_history_working_tree_preserved": _check(tree),
                    "current_history_head_preserved": _check(head)})


def _screen_grade(dest: Path, truth: dict) -> dict:
    path = dest / TASKS[2] / "output" / "screen.json"
    expected = truth["expected_screen"]
    results = {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except BaseException as exc:
        results["json_schema"] = (False, f"{type(exc).__name__}: {str(exc)[:300]}")
        for row in expected["roles"]:
            results[row["job_id"] + "_evidence_decision"] = (False, "JSON unavailable")
        results["selected_ids_exact"] = (False, "JSON unavailable")
        return _report(results)
    def schema():
        assert type(value) is dict and set(value) == {"as_of", "roles", "selected_ids"}, "top-level schema differs"
        assert value["as_of"] == AS_OF, "wrong cutoff"
        assert type(value["roles"]) is list and len(value["roles"]) == 10, "need ten role records"
        assert type(value["selected_ids"]) is list, "selected_ids must be list"
        for got, want in zip(value["roles"], expected["roles"]):
            assert type(got) is dict and got.keys() == want.keys(), "role schema differs"
            assert got["job_id"] == want["job_id"], "role order or id differs"
            for key in ("city_eligible", "technical", "selected"):
                assert type(got[key]) is bool, f"{key} must be bool"
            assert got["status"] in ("open", "closed", "unknown")
            assert got["recent_recruitment"] in ("official_confirmed", "self_report_only", "none")
            assert got["hc"] in ("confirmed_available", "confirmed_zero", "unknown")
            for key in ("status_evidence", "recent_recruitment_evidence", "hc_evidence"):
                assert got[key] is None or type(got[key]) is str, "evidence id type differs"
    results["json_schema"] = _check(schema)
    for index, want in enumerate(expected["roles"]):
        def row_check(index=index, want=want):
            _assert_result(value["roles"][index], want)
        results[want["job_id"] + "_evidence_decision"] = _check(row_check)
    results["selected_ids_exact"] = _check(lambda: _assert_result(value["selected_ids"], expected["selected_ids"]))
    return _report(results)


def _code_grade(path: Path, kind: str, names: tuple[str, ...]) -> dict:
    if not path.is_file():
        return _report({name: (False, "output module missing") for name in names})
    # Run untrusted subject modules in a fresh interpreter. This is process
    # isolation for repeatable tests, not a claimed adversarial security sandbox.
    with tempfile.TemporaryDirectory(prefix="grader-", dir=Path(__file__).resolve().parent) as temp:
        temp_path = Path(temp)
        result_path = temp_path / "result.json"
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-B", str(Path(__file__).resolve()),
                 "_worker", kind, str(path.resolve()), str(result_path)],
                cwd=temp_path, stdin=subprocess.DEVNULL, capture_output=True,
                timeout=12,
            )
            if not result_path.is_file():
                detail = f"worker failed (exit {completed.returncode})"
                return _report({name: (False, detail) for name in names})
            result = json.loads(result_path.read_text(encoding="utf-8"))
            assert set(result) == set(names), "worker check set differs"
            return _report({name: (bool(result[name][0]), result[name][1]) for name in names})
        except subprocess.TimeoutExpired:
            return _report({name: (False, "module import/test timeout") for name in names})
        except BaseException as exc:
            return _report({name: (False, f"{type(exc).__name__}: {str(exc)[:300]}") for name in names})


def grade(dest: Path, truth: dict) -> dict:
    """Return objective named checks grouped by task, plus input integrity.

    Each task result has passed: bool, checks: dict[str,bool], details for failed
    checks. No aggregate score or causal benefit claim is inferred here.
    """
    dest = Path(dest).resolve()
    if truth.get("suite_version") != SUITE_VERSION:
        raise ValueError("truth suite_version mismatch")
    report = {
        TASKS[0]: _history_grade(dest, truth[TASKS[0]]),
        TASKS[1]: _code_grade(dest / TASKS[1] / "output" / "budget.py", "budget", BUDGET_CHECK_NAMES),
        TASKS[2]: _screen_grade(dest, truth[TASKS[2]]),
        TASKS[3]: _code_grade(dest / TASKS[3] / "output" / "queue_payload.py", "retry", RETRY_CHECK_NAMES),
    }
    # Guard the fixed inputs separately from task behavior; do not silently
    # award completion when a subject has changed the specification/fixture.
    protected = truth["protected_input_sha256"]
    def preserved():
        for relative, expected_digest in protected.items():
            file = dest / relative
            assert file.is_file(), f"protected input missing: {relative}"
            assert hashlib.sha256(file.read_bytes()).hexdigest() == expected_digest, f"protected input changed: {relative}"
        expected_paths = set(protected)
        actual_paths = {
            file.relative_to(dest).as_posix() for file in dest.rglob("*")
            if file.is_file() and ".git" not in file.relative_to(dest).parts
            and "output" not in file.relative_to(dest).parts
        }
        assert actual_paths == expected_paths, "file added outside output/"
    report["input_integrity"] = _report({"protected_input_files_preserved": _check(preserved)})
    return report


def _reference_outputs(dest: Path, truth: dict) -> None:
    out = dest / TASKS[0] / "output"
    _json(out / "choice.json", {"commit": truth[TASKS[0]]["selected_commit"]})
    with zipfile.ZipFile(out / "reader.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in _unpack(truth[TASKS[0]]["selected_files_b64"]).items():
            archive.writestr(name, data)
    _write(dest / TASKS[1] / "output" / "budget.py", BUDGET_REFERENCE)
    _json(dest / TASKS[2] / "output" / "screen.json", truth[TASKS[2]]["expected_screen"])
    _write(dest / TASKS[3] / "output" / "queue_payload.py", RETRY_REFERENCE)


def _all_passed(report: dict) -> bool:
    return all(part["passed"] for part in report.values())


def selfcheck() -> dict:
    """Verify correct artifacts pass and realistic seeded bad artifacts fail.

    All temporary data is created beside this module, on D when installed in
    the requested support path. No experiment output or arm is read.
    """
    with tempfile.TemporaryDirectory(prefix="selfcheck-", dir=Path(__file__).resolve().parent) as temp:
        subject = Path(temp) / "subject"
        truth = build(subject)
        _reference_outputs(subject, truth)
        good = grade(subject, truth)
        assert _all_passed(good), f"reference artifacts failed: {good}"
        out = subject / TASKS[0] / "output"
        _json(out / "choice.json", {"commit": truth[TASKS[0]]["current_head"]})
        with zipfile.ZipFile(out / "reader.zip", "w") as archive:
            for name, data in _unpack(truth[TASKS[0]]["current_files_b64"]).items():
                archive.writestr(name, data)
        _write(subject / TASKS[1] / "output" / "budget.py", BUDGET_SEED)
        bad_screen = copy.deepcopy(truth[TASKS[2]]["expected_screen"])
        bad_screen["roles"][1].update(status="open", status_evidence="J02-R1", selected=True)
        bad_screen["roles"][2].update(status="open", status_evidence="J03-O2", selected=True)
        bad_screen["roles"][5].update(hc="confirmed_available", hc_evidence="J06-C1")
        bad_screen["roles"][9].update(status="closed", status_evidence="J10-X1", selected=False,
                                      hc="confirmed_zero", hc_evidence="J10-X1")
        bad_screen["selected_ids"] = [row["job_id"] for row in bad_screen["roles"] if row["selected"]]
        _json(subject / TASKS[2] / "output" / "screen.json", bad_screen)
        _write(subject / TASKS[3] / "output" / "queue_payload.py", RETRY_SEED)
        bad = grade(subject, truth)
        assert all(not bad[task]["passed"] for task in TASKS), f"seed escaped detection: {bad}"
        assert bad["input_integrity"]["passed"], "output-only seeds altered input"
        # Independently verify the history-preservation check, not only selection.
        _write(subject / TASKS[0] / "history" / "reader.css", "tampered\n")
        tampered = grade(subject, truth)
        assert not tampered[TASKS[0]]["checks"]["current_history_working_tree_preserved"]
        assert not tampered["input_integrity"]["passed"]
        return {"passed": True, "suite_version": SUITE_VERSION,
                "reference_artifacts_all_passed": True,
                "seeded_bad_rejected_by_task": {task: not bad[task]["passed"] for task in TASKS},
                "seeded_bad_failed_checks": {
                    task: [name for name, passed in bad[task]["checks"].items() if not passed]
                    for task in TASKS},
                "history_tamper_detected": True}


def _worker(kind: str, path: Path, result_path: Path) -> None:
    names = BUDGET_CHECK_NAMES if kind == "budget" else RETRY_CHECK_NAMES
    try:
        spec = importlib.util.spec_from_file_location("subject_output", path)
        if spec is None or spec.loader is None:
            raise ImportError("module could not be loaded")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = _budget_tests(module) if kind == "budget" else _retry_tests(module)
    except BaseException as exc:
        result = {name: (False, f"{type(exc).__name__}: {str(exc)[:300]}") for name in names}
    _json(result_path, result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selfcheck")
    build_parser = sub.add_parser("build")
    build_parser.add_argument("dest", type=Path)
    build_parser.add_argument("--truth-out", required=True, type=Path,
                              help="hidden truth path outside subject destination")
    grade_parser = sub.add_parser("grade")
    grade_parser.add_argument("dest", type=Path)
    grade_parser.add_argument("--truth", required=True, type=Path)
    worker_parser = sub.add_parser("_worker", help=argparse.SUPPRESS)
    worker_parser.add_argument("kind", choices=("budget", "retry"))
    worker_parser.add_argument("path", type=Path)
    worker_parser.add_argument("result_path", type=Path)
    args = parser.parse_args()
    if args.command == "selfcheck":
        print(json.dumps(selfcheck(), ensure_ascii=False, indent=2))
    elif args.command == "build":
        dest = args.dest.resolve()
        truth_path = args.truth_out.resolve()
        if truth_path == dest or dest in truth_path.parents:
            raise ValueError("truth must be kept outside subject destination")
        truth = build(dest)
        _json(truth_path, truth)
        print(json.dumps({"built": str(dest), "truth": str(truth_path), "suite_version": SUITE_VERSION}))
    elif args.command == "grade":
        truth = json.loads(args.truth.read_text(encoding="utf-8"))
        print(json.dumps(grade(args.dest, truth), ensure_ascii=False, indent=2))
    else:
        _worker(args.kind, args.path, args.result_path)


if __name__ == "__main__":
    main()
