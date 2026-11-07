#!/usr/bin/env python3
"""Run a small, explicitly reconstructed reader case in two storage designs.

The case illustrates known user corrections but does not claim these events,
dates, agent identities, or artifacts actually occurred in this trial.
The factual repository study is recorded separately by the researcher.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from trace import append, feedback, load, view


def run(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    journal = out / "events.jsonl"
    if journal.exists() or (out / "WORK.md").exists():
        raise ValueError("choose a new output directory; previous work is not overwritten")
    origin = "reconstructed_scenario"

    def add(kind, topic, summary, effect, **extra):
        return append(journal, kind=kind, topic=topic, summary=summary, effect=effect,
                      origin=origin, **extra)

    add("commitment", "投入", "本例保留N12/R4/D3/V3；显式指定的L3不自动下调。",
        "改变方法、资源和拆分方向；本例不认证完成次数。",
        floor=dict(N=12, R=4, D=3, V=3), investment=dict(N=12, R=4, D=3, V=3),
        explicit="L(3)", basis="本次设计委托，不是正在运行的P_run替代物。")
    add("request", "读物形态", "组合原PDF/EPUB中所需的内容，提供可直接阅读的文件。",
        "需讨论选段、知识依赖和阅读顺序；不能自行推导成重写整书。",
        exact_text="情境重建，非逐字用户引文。")
    correction = add("correction", "读物形态", "用户纠正：保留原文块或原页；不以全量清洗、阅读器为前置。",
                     "停止统一叙事路线；复用原件做组装样本。", actor="user",
                     basis="任务交接所述历史案例；本次未检查原始书籍。")
    parked = add("decision", "局部重排", "全量重排被搁置，因为缺少足以抵偿投入的阅读收益。",
                 "先采用原页；保留局部重排的研究空间。", decision="parked",
                 relates=[correction["id"]],
                 reopen_when="原页样本出现无法靠选段或局部附注解决的明确障碍。")
    task = add("dispatch", "跨章依赖", "给独立研究线路：检查本轮选段是否隐去真实跨章依赖，返回具体位置与处理建议。",
               "Main继续组装样本；子任务可据材料改问题，不预定三层任务树。",
               actor="Main -> viewpoint-reader", basis="仅交目标、选择片段与原章节位置，不灌入全部主线理由。")
    dissent = add("dissent", "读物形态", "异议：照页组装仍可能割裂知识；有目录不代表可学。",
                  "先保留异议，需查看依赖内容后决定，暂不改成全量重写。",
                  actor="viewpoint-reader", relates=[task["id"]])
    result = add("return", "跨章依赖", "研究结果：选段缺6.3多层网络，上游代码依赖与脚注应一并定位。",
                 "原页路线仍可行，但需对照相邻节实际范围补选。",
                 actor="viewpoint-reader", relates=[task["id"]],
                 artifact="情境中的返回笔记，非本次已生成书籍。")
    before_handling = feedback(load(journal))
    assert before_handling[0]["state"] == "已回传，Main处理未记录"
    add("decision", "跨章依赖", "Main采纳补选6.3与脚注；未采纳把整个参考手册并入正文。",
        "修改选段计划，保留出处链接；仍需在主要读物中落实。",
        decision="部分采纳", relates=[result["id"], dissent["id"]],
        reopen_when="若补选后仍无法解释原代码所依赖的定义，再扩大范围。")
    deferred_task = add("dispatch", "锚点", "另派一次跳转研究：同名anchor是否跨章误跳？",
                        "返回具体跳转对；Main继续处理依赖内容。", actor="Main -> link-study")
    deferred_result = add("return", "锚点", "发现跨章同名anchor误跳；建议只给组装容器添加命名空间。",
                          "建议已回传；本次情境故意不补Main处理，供恢复时取回。",
                          relates=[deferred_task["id"]], actor="link-study")
    add("reopen", "局部重排", "有代表性的样本出现跨页图注分离，触发T0004的条件；重开受影响两页的局部方案。",
        "对照原页加附注与局部重排两种小样，不恢复全库清洗。", relates=[parked["id"]])
    add("effort", "投入", "依赖与跳转问题改变了工作量，投入目标上调为N16/R5/D4/V3。",
        "再分出图注试作；现有跨章依赖线路继续，方法和任务拆分可重新组合。",
        investment=dict(N=16, R=5, D=4, V=3),
        method="原页路线保留；独立研究与局部试作并行；不新增API成本。",
        basis="任务难度的工作判断；没有把12个事件当N12。")
    add("pitfall", "原文拼接", "发现原文的内部ID只在单章唯一，直接合并会让跨章跳转命中错误目标。",
        "同类组装先读真实跳转对，再按源章节命名空间修复；不全局清洗整库。",
        relates=[deferred_result["id"]], scope="保留原HTML片段的跨章组装任务",
        unless="源文件已使用全局唯一ID，或没有需要保留的内部跳转。",
        basis="本例据已交接问题重建；实际使用前回到对应原文件。")

    events = load(journal)
    resumed = view(events, topic="局部重排")
    assert "T0004" in resumed and "跨页图注分离" in resumed
    assert "已回传，Main处理未记录" in resumed
    assert "N16/R5/D4/V3" in resumed
    assert commitment_floor_unchanged(events)
    original_size = journal.stat().st_size
    try:
        add("effort", "投入", "尝试因省事降档。", "应拒绝改写既有责任。",
            investment=dict(N=3, R=1, D=1, V=1))
    except ValueError as error:
        downshift_result = str(error)
    else:
        raise AssertionError("unexpected downshift acceptance")
    assert journal.stat().st_size == original_size

    # Alternative A is actual editable prose; no JSON blocks or event parser.
    work = """# 原文组装：一份公开工作笔记

这是由历史问题重建的设计情境；不是本次执行记录或已制作书籍。

## 用户目标
组合原PDF/EPUB的所需内容，交付能直接打开阅读的文件。选段与顺序仍需实质讨论。

## 交付形态与价值
保留原文块或原页，使跨章依赖、图表、脚注与跳转可用。

## 用户纠正与已确认要求
不以前置全量清洗、统一叙事或新阅读器替代原文组装。此笔记不代替与用户讨论何谓“知识完整”。
投入下限N12/R4/D3/V3；显式L3保留；当前工作投入目标N16/R5/D4/V3，不是已完成次数。

## 当前关键问题
原页中图注跨页时，局部附注和仅重排两页，哪种更有利于保真阅读？

## 研究、竞争解释与方案

### 主线决定与重开
全量重排原因：曾以为统一内容才能保持完整。用户纠正后搁置，因为没有显示足够阅读收益。
重开条件：原页样本存在无法靠选段或局部附注解决的具体阅读障碍。
现在图注跨页分离触发了局部研究；只比较受影响两页的附注与重排，不恢复全库清洗。

### 派发、异议与主线处理
Main给viewpoint-reader目标和原章节位置，研究跨章依赖；Main继续组装。
该线路异议：有目录仍可能割裂知识。回传缺6.3多层网络、代码依赖与脚注。
Main处理：采纳补6.3与脚注，未采纳将整份参考手册放正文；需落实读物。
另给link-study实际跳转对，回传跨章同名anchor误跳，建议源章节命名空间。
**该跳转结果已收到，Main尚未处理。** 不能以“代理已结束”标作落实。
投入随问题上调；图注研究与依赖研究可另拆、合并或撤回；没有固定任务树。

### 任务内避坑线索
跨章原HTML组装时，先看原ID是否只在章节内唯一；若有错跳，局部命名空间修复。
适用条件：确有跨章内部跳转。失效条件：源ID已全局唯一或无跳转。不泛化成所有任务的强制扫描。
本情境未取回原文件；使用这条线索时仍需定位真实错误与原页。

## 当前产物与可继续的位置
只有设计情境，没有本次已生成的书；先处理link-study返回结果，再继续代表片段比较。

## 值得继续的工作
带用户纠正、当前两页样本和原始图注问题继续；按实际价值重开，不按日志行数停工。
"""
    (out / "WORK.md").write_text(work, encoding="utf-8", newline="\n")
    (out / "VIEW.md").write_text(resumed, encoding="utf-8", newline="\n")
    return dict(events=len(events), markdown_bytes=(out / "WORK.md").stat().st_size,
                journal_bytes=journal.stat().st_size,
                untreated=[row for row in feedback(events) if row["state"] == "已回传，Main处理未记录"],
                downshift=downshift_result)


def commitment_floor_unchanged(events):
    return events[0]["floor"] == dict(N=12, R=4, D=3, V=3) and events[0]["explicit"] == "L(3)"


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    import json
    print(json.dumps(run(args.out.resolve()), ensure_ascii=False, indent=2))
