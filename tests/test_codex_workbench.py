from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runtime.codex_workbench import (
    GOAL, DELIVERY, STEERING, QUESTION, RESEARCH, RESULT, NEXT,
    create_workbench, context_packet, read_material, sections, topic_index,
)

ROOT = Path(__file__).resolve().parents[1]


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
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
        with self.assertRaisesRegex(ValueError, '具体研究问题'):
            context_packet(self.work, kind='V')

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
        result = subprocess.run(cli+['init', '--request', str(request), '--work', str(output)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(original, output.read_bytes())


if __name__ == '__main__':
    unittest.main()
