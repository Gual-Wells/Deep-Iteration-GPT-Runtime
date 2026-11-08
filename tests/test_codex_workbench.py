from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runtime.codex_workbench import (
    GOAL, DELIVERY, STEERING, QUESTION, RESEARCH, RESULT, NEXT,
    create_workbench, context_packet, read_material, sections, topic_index, record_work,
)

ROOT = Path(__file__).resolve().parents[1]


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='workbench-test-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / 'WORK.md'
        request = '保留原文，组装成可读文件。\n## 原请求自带标题\n```python\nx = 1\n```\n'
        text = create_workbench(request)
        self.request = request
        values = {
            DELIVERY: '实际打开和跳转方便，内容保持连续。',
            STEERING: '用户已经明确：不需要手机适配。',
            QUESTION: '原页直接组合是否满足用途？',
            RESEARCH: '### 原页路线\n用代表内容研究直接组合，尚需实际试作。\n\n### 搁置路线\n过期的大型清洗方案，不应在当前上下文反复出现。',
            RESULT: '可继续的方案在 current.md。',
            NEXT: '检验关键材料是否适合原页组合。',
        }
        for title, value in values.items():
            text = text.replace(f'## {title}\n\n', f'## {title}\n{value}\n\n')
        self.work.write_text(text, encoding='utf-8', newline='\n')
        (self.root / 'material.txt').write_text('原材料第一行\n关键事实\n另一段事实\n', encoding='utf-8', newline='\n')
        (self.root / 'current.md').write_text('当前候选：保留原页，目录跳转。\n', encoding='utf-8', newline='\n')

    def test_original_request_with_markdown_survives_as_one_goal(self):
        text = self.work.read_text(encoding='utf-8')
        found = sections(text)
        goal = next(s for s in found if s.title == GOAL)
        self.assertIn(self.request, goal.text)
        self.assertFalse(any(s.title == '原请求自带标题' for s in found))

    def test_focus_retains_user_correction_and_only_selected_research(self):
        packet = context_packet(self.work, topic='原页路线')
        self.assertIn('不需要手机适配', packet)
        self.assertIn(self.request, packet)
        self.assertIn('用代表内容研究直接组合', packet)
        self.assertIn('可继续的方案在 current.md', packet)
        self.assertNotIn('过期的大型清洗方案', packet)

    def test_material_ranges_are_relative_to_workbench_and_have_locations(self):
        packet = context_packet(self.work, materials=('material.txt:2-3',))
        self.assertIn((self.root / 'material.txt').as_posix()+':2-3', packet)
        self.assertIn('2: 关键事实\n3: 另一段事实', packet)
        self.assertNotIn('1: 原材料第一行', packet)

    def test_controlled_challenge_uses_chosen_candidate_without_main_rationale(self):
        packet = context_packet(
            self.work, kind='D', question='另一条路线能否直接改变生产方式？',
            candidates=('current.md',), materials=('material.txt:2',),
        )
        self.assertIn('不需要手机适配', packet)
        self.assertIn('当前候选：保留原页', packet)
        self.assertIn('2: 关键事实', packet)
        self.assertNotIn('用代表内容研究直接组合', packet)
        self.assertNotIn('检验关键材料是否适合原页组合', packet)

    def test_viewpoint_packet_carries_actual_question_and_user_goal(self):
        packet = context_packet(self.work, kind='V', question='从真实阅读过程持续研究依赖关系。')
        self.assertIn('从真实阅读过程持续研究依赖关系', packet)
        self.assertIn(self.request, packet)
        self.assertNotIn('当前候选：保留原页', packet)
        scout = context_packet(self.work, kind='V')
        self.assertIn('领域身份可以在研究讨论中形成或修订', scout)
        self.assertIn(self.request, scout)
        self.assertNotIn('用代表内容研究直接组合', scout)
        disruptive = context_packet(self.work, kind='D')
        self.assertIn('具体反叛对象与旗帜可以由研究形成', disruptive)
        self.assertNotIn('检验关键材料是否适合原页组合', disruptive)

    def test_explicit_sections_preserve_existing_freeform_goal_and_corrections(self):
        existing = self.root / 'existing-work.md'
        original = (
            '# 原有项目笔记\n\n## 用户目标 U0\n````text\n做实际工程升级。\n````\n\n'
            '## 已有用户决定与纠正\n语言气质的纠正不能取消明确的工程委托。\n\n'
            '## 本轮原话\n这是举例，不必专门定位那篇论文。\n\n'
            '## 当前关键问题\n主线认为应再建一套流程。\n\n'
            '## 研究、竞争解释与方案\n主线尚未验证的整套解释。\n\n'
            '## 值得继续的工作\n不应灌入独立者的主线下一步。\n'
        )
        existing.write_text(original, encoding='utf-8')
        packet = context_packet(
            existing, kind='D', goal_topic='用户目标 U0',
            corrections_topics=('已有用户决定与纠正', '本轮原话'),
        )
        for fragment in ('做实际工程升级', '不能取消明确的工程委托', '不必专门定位那篇论文'):
            self.assertIn(fragment, packet)
        for fragment in ('主线认为应再建', '主线尚未验证', '不应灌入独立者'):
            self.assertNotIn(fragment, packet)
        self.assertEqual(existing.read_text(encoding='utf-8'), original)

    def test_explicit_goal_does_not_silently_compete_with_request_or_ambiguous_section(self):
        request = self.root / 'another-request.txt'
        request.write_text('另一个来源中的原始委托。', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '请选择一个原始目标来源'):
            context_packet(self.work, request=request, goal_topic=GOAL)
        self.work.write_text(self.work.read_text(encoding='utf-8')+'\n### 同名纠正\nA\n\n## 同名纠正\nB\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '纠正小节必须唯一匹配'):
            context_packet(self.work, corrections_topics=('同名纠正',))
        with self.assertRaisesRegex(ValueError, '目标小节必须唯一匹配'):
            context_packet(self.work, goal_topic='不存在')

    def test_selected_experience_is_optional_and_does_not_replace_current_correction(self):
        from runtime.codex_experience import capture_candidate, write_candidate
        source = self.root / 'earlier-feedback.txt'
        source.write_text('原话：缺激情指语言、行为和策略气质。\n', encoding='utf-8')
        candidate = self.root / 'history.json'
        write_candidate(candidate, capture_candidate(
            '历史解释：气质批评不能只用组织机制回答。条件不同仍须实施本次工程。',
            sources=['earlier-feedback.txt'], base=self.root,
        ))
        default = context_packet(self.work)
        self.assertNotIn('历史解释', default)
        selected = context_packet(self.work, kind='V', experiences=('history.json',))
        self.assertIn('不需要手机适配', selected)
        self.assertIn('条件不同仍须实施本次工程', selected)
        self.assertNotIn('用代表内容研究直接组合', selected)
        with self.assertRaisesRegex(ValueError, '不会被静默截断'):
            context_packet(self.work, experiences=('history.json',), max_chars=len(default)+10)

    def test_context_budget_does_not_silently_truncate_or_change_work(self):
        before = self.work.read_bytes()
        with self.assertRaisesRegex(ValueError, '不会被静默截断'):
            context_packet(self.work, max_chars=100)
        self.assertEqual(before, self.work.read_bytes())

    def test_topics_find_material_for_reopening_dormant_research(self):
        index = topic_index(self.work)
        self.assertIn('搁置路线', index)
        self.assertIn(self.work.as_posix()+':', index)
        reopened = context_packet(self.work, topic='搁置路线')
        self.assertIn('过期的大型清洗方案', reopened)

    def test_bad_selected_range_is_not_replaced_by_a_different_excerpt(self):
        with self.assertRaisesRegex(ValueError, '行范围超出'):
            read_material('material.txt:2-20', base=self.root)

    def test_pdf_reference_does_not_trigger_a_fake_text_or_full_conversion_path(self):
        with self.assertRaisesRegex(ValueError, '现有阅读/页段工具'):
            read_material('source.pdf:3-10', base=self.root)

    def test_existing_freeform_notes_do_not_need_conversion_to_the_template(self):
        notes = self.root / 'existing.md'
        text = '# 已有研究\n\n## 路线比较\n实际材料支持直接组合，仍需研究依赖。\n\n## 旧讨论\n暂不选入。\n'
        notes.write_text(text, encoding='utf-8')
        request = self.root / 'actual-request.txt'
        request.write_text(self.request, encoding='utf-8')
        packet = context_packet(notes, request=request, topic='路线比较')
        self.assertIn(self.request, packet)
        self.assertIn('实际材料支持直接组合', packet)
        self.assertNotIn('暂不选入', packet)
        self.assertEqual(notes.read_text(encoding='utf-8'), text)

    def test_record_retrieves_a_real_correction_without_replacing_goal_or_result(self):
        original = self.work.read_text(encoding='utf-8')
        self.work.write_bytes(original.replace('\n', '\r\n').encode('utf-8-sig'))
        record_work(self.work, '父节通用判断，不属于任何单独路线。')
        note = '收到返回：不能重写原文。\n## 这只是返回中的标题\nMain决定保留原页；组装尚未执行。'
        location = record_work(self.work, note, topic='原页路线', kind='返回与取舍', refs=('source.pdf:12',))
        raw = self.work.read_bytes()
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n', raw.replace(b'\r\n', b''))
        packet = context_packet(self.work, topic='原页路线')
        self.assertIn(self.request, packet)
        self.assertIn('不需要手机适配', packet)
        self.assertIn('组装尚未执行', packet)
        self.assertIn('source.pdf:12', packet)
        self.assertNotIn('父节通用判断', packet)
        self.assertNotIn('父节通用判断', context_packet(self.work, topic='搁置路线'))
        self.assertIn('父节通用判断', context_packet(self.work))
        self.assertEqual([s.title for s in sections(original)], [s.title for s in sections(raw.decode('utf-8-sig'))])
        self.assertTrue(location.startswith(self.work.as_posix()+':'))
        self.assertEqual(
            next(s.text for s in sections(original) if s.title == RESULT),
            next(s.text for s in sections(raw.decode('utf-8-sig')) if s.title == RESULT),
        )

    def test_record_does_not_guess_between_duplicate_or_missing_topics(self):
        self.work.write_text(self.work.read_text(encoding='utf-8')+'\n## 原页路线\n另一处材料\n', encoding='utf-8')
        before = self.work.read_bytes()
        for topic in ('原页路线', '不存在的小节'):
            with self.subTest(topic=topic), self.assertRaisesRegex(ValueError, '唯一匹配'):
                record_work(self.work, '不应写入错误位置。', topic=topic)
            self.assertEqual(before, self.work.read_bytes())

    def test_cli_creates_then_reads_work_and_preserves_existing_notes(self):
        cli = [sys.executable, '-B', str(ROOT / 'tools/codex_workbench.py')]
        request = self.root / 'request.txt'
        output = self.root / 'new-work.md'
        request.write_text(self.request, encoding='utf-8')
        result = subprocess.run(cli+['init', '--request', str(request), '--work', str(output)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        original = output.read_bytes()
        result = subprocess.run(cli+['focus', '--work', str(output)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(self.request, result.stdout)
        note = self.root / 'return.txt'
        note.write_text('已收到研究；尚未组装，继续保留原文。', encoding='utf-8')
        result = subprocess.run(cli+['record', '--work', str(output), '--text-file', str(note), '--kind', '返回'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('尚未组装', context_packet(output))
        original = output.read_bytes()
        result = subprocess.run(cli+['init', '--request', str(request), '--work', str(output)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(original, output.read_bytes())

    def test_cli_uses_existing_sections_for_open_research_without_main_rationale(self):
        cli = [sys.executable, '-B', str(ROOT / 'tools/codex_workbench.py')]
        existing = self.root / 'custom.md'
        existing.write_text(
            '# 自由笔记\n## 真实原始委托\n完成代码升级。\n\n'
            '## 用户已说清的事\n论文只是例子，仍需研究真实方法。\n\n'
            '## 研究、竞争解释与方案\n不应默认转交的Main解释。\n', encoding='utf-8',
        )
        result = subprocess.run(
            cli+['challenge', '--work', str(existing), '--kind', 'V',
                 '--goal-topic', '真实原始委托', '--corrections-topic', '用户已说清的事'],
            capture_output=True, text=True, encoding='utf-8',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('完成代码升级', result.stdout)
        self.assertIn('论文只是例子', result.stdout)
        self.assertIn('领域身份可以在研究讨论中形成或修订', result.stdout)
        self.assertNotIn('不应默认转交的Main解释', result.stdout)


if __name__ == '__main__':
    unittest.main()
