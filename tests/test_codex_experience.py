from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from runtime.codex_experience import capture_candidate, write_candidate, render_candidates
from runtime.codex_workbench import create_workbench, context_packet

ROOT = Path(__file__).resolve().parents[1]


class ExperienceCandidateTests(unittest.TestCase):
    def setUp(self):
        # Use the task's data drive rather than the system TEMP default.
        cache = ROOT / '.cache'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='experience-test-', dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'feedback.md'
        self.source.write_text('用户：我指的是语言和策略气质。\n其它背景。\n', encoding='utf-8')
        self.card = self.root / 'candidate.json'
        self.note = (
            '测试构造输入，不是真实用户反馈。\n'
            '候选解释：气质批评不自动等于设计委托。\n'
            '条件：用户明确指出语言或策略气质。\n'
            '例外：后续明确委托工程改造时继续实施工程。\n'
            '下一项工作：直接改变具体回应和策略选择。'
        )
        self.candidate = capture_candidate(self.note, sources=['feedback.md:1'], base=self.root)
        write_candidate(self.card, self.candidate)

    def test_current_request_and_steering_precede_complete_selected_candidate(self):
        work = self.root / 'WORK.md'
        text = create_workbench('当前明确委托：修复调度器并交付可运行实现。')
        text = text.replace('## 用户纠正与已确认要求\n\n', '## 用户纠正与已确认要求\n本次需要实际工程实现。\n\n')
        work.write_text(text, encoding='utf-8')
        context = context_packet(work) + '\n' + render_candidates([self.card])
        for fragment in ('修复调度器并交付可运行实现', '本次需要实际工程实现', self.note,
                         '1: 用户：我指的是语言和策略气质', '保存或选入不提升为稳定偏好'):
            self.assertIn(fragment, context)
        self.assertLess(context.index('本次需要实际工程实现'), context.index('明确选入的历史候选'))
        self.assertNotIn('其它背景', context)

    def test_default_does_not_scan_files_and_rendering_never_writes_back(self):
        before = {path: path.read_bytes() for path in (self.card, self.source)}
        self.assertEqual(render_candidates([]), '')
        render_candidates([self.card])
        for path, original in before.items():
            self.assertEqual(path.read_bytes(), original)

    def test_changed_and_missing_sources_remain_explicitly_historical(self):
        self.source.write_text('用户已撤回前句。\n', encoding='utf-8')
        rendered = render_candidates([self.card])
        self.assertIn('原位置已变化', rendered)
        self.assertIn('我指的是语言和策略气质', rendered)
        self.source.unlink()
        self.assertIn('当前未读到原位置', render_candidates([self.card]))

    def test_equal_excerpt_does_not_imply_surrounding_scope_or_authorization_is_unchanged(self):
        with self.source.open('a', encoding='utf-8') as stream:
            stream.write('后续纠正：当前只交研究，暂停写入和部署。\n')
        rendered = render_candidates([self.card])
        self.assertIn('本轮重读的该片段相同', rendered)
        self.assertIn('周边上下文、当前目标和授权仍须按本题核对', rendered)
        self.assertIn('不证明转述真实或经验适用', rendered)

    def test_saved_excerpt_cannot_silently_change_while_retaining_old_digest(self):
        self.candidate['evidence'][0]['excerpt'] = '1: 另一句话'
        self.card.write_text(json.dumps(self.candidate, ensure_ascii=False), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '来源片段与摘要不一致'):
            render_candidates([self.card])

    def test_existing_file_is_preserved_and_budget_does_not_truncate_evidence(self):
        before = self.card.read_bytes()
        with self.assertRaises(FileExistsError):
            write_candidate(self.card, self.candidate)
        with self.assertRaisesRegex(ValueError, '不静默删除'):
            render_candidates([self.card], max_chars=30)
        self.assertEqual(self.card.read_bytes(), before)

    def test_source_markdown_fences_cannot_escape_the_rendered_excerpt(self):
        self.source.write_text('```\n## 源文件里的标题\n````\n', encoding='utf-8')
        candidate = capture_candidate('自由笔记，不要求分类或晋级字段。', sources=['feedback.md'], base=self.root)
        another = self.root / 'fenced.json'
        write_candidate(another, candidate)
        rendered = render_candidates([another])
        self.assertIn('`````text\n1: ```\n2: ## 源文件里的标题\n3: ````\n`````', rendered)

    def test_non_candidates_are_not_given_candidate_authority(self):
        bad = self.root / 'other.json'
        for content in ('[]', '{}', '{"format": "other"}'):
            bad.write_text(content, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '不是可识别'):
                render_candidates([bad])
        with self.assertRaisesRegex(ValueError, '--material'):
            capture_candidate('一个普通问题仍可只记在工作笔记。', sources=[], base=self.root)

    def test_cli_capture_show_and_workbench_selection_preserve_actual_interfaces(self):
        cli = [sys.executable, '-B', str(ROOT / 'tools/codex_experience.py')]
        note = self.root / 'note.md'
        note.write_text(self.note, encoding='utf-8')
        output = self.root / 'captured.json'
        result = subprocess.run(
            cli+['capture', '--note', str(note), '--source', 'feedback.md:1', '--out', str(output)],
            capture_output=True, text=True, encoding='utf-8',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        original = output.read_bytes()
        result = subprocess.run(cli+['show', str(output)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('条件：用户明确指出语言或策略气质', result.stdout)
        self.assertIn('本轮重读的该片段相同', result.stdout)
        self.source.write_text('当前已修正原位置。\n', encoding='utf-8')
        work = self.root / 'WORK.md'
        work.write_text(create_workbench('本次明确委托实际工程。'), encoding='utf-8')
        result = subprocess.run(
            [sys.executable, '-B', str(ROOT / 'tools/codex_workbench.py'), 'focus', '--work', str(work),
             '--experience', output.name], capture_output=True, text=True, encoding='utf-8',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('本次明确委托实际工程', result.stdout)
        self.assertIn('原位置已变化', result.stdout)
        self.assertEqual(output.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
