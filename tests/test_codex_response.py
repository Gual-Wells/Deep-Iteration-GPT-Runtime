from __future__ import annotations

import unittest

from runtime.codex_response import render_response, render_work_table, validate_response


class ResponseTests(unittest.TestCase):
    def report(self, **changes):
        data = {
            'result': '两个条件都完成了给定任务，现有观察不能证明新版更好。',
            'key_changes': '把“格式检查通过”收窄为结构事实，独立保留真实效果问题。',
            'work_process': render_work_table([('未记录逐项边界', '对照已选原件；不推算逐轮耗时。')]),
            'verification_limits': '核对了报告正文，没有重新运行历史试验。',
            'parameters': '这是格式试样；历史参数不追认为本次实际。',
        }
        data.update(changes)
        return data

    def test_research_argument_and_real_artifact_links_remain_in_body(self):
        argument = '### 为什么保留原结论\n\n已有证据只能支持持平。\n\n[原件](https://example.org/report.html)补充细节。'
        text = render_response(self.report(result=argument))
        self.assertIn(argument, text)
        validate_response(text)

    def test_html_and_fake_section_titles_inside_code_do_not_change_structure(self):
        code = '修复例子：\n\n````html\n<div>样本</div>\n## 第六段是假标题\n```\n````\n\n`<details>只是代码</details>` 与 ``a ` <b>`` 都是字面量。'
        validate_response(render_response(self.report(result=code)))

    def test_markdown_autolink_and_angle_brackets_are_prose(self):
        validate_response(render_response(self.report(result='正文来源 <https://example.org/report>，联系 <user@example.org>，当 a < b 时保留条件。')))

    def test_multiline_inline_html_sample_is_literal_code(self):
        validate_response(render_response(self.report(result='例子 `<div>\n这里是字面量\n</div>` 不携带正文。')))

    def test_extra_top_section_reordered_sections_and_html_container_fail(self):
        valid = render_response(self.report())
        invalid = [
            valid.replace('## 关键变化', '## 更多\n\n新顶层段落\n\n## 关键变化'),
            valid.replace('## 结果', '## 参数', 1),
            valid.replace('## 结果', '<details>\n\n## 结果', 1) + '\n</details>',
            valid.replace('## 结果', '```markdown\n## 结果', 1) + '\n```',
        ]
        for text in invalid:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    validate_response(text)

    def test_empty_field_and_unclosed_code_are_not_complete_reports(self):
        for data in (self.report(parameters='  '), self.report(result='```python\nprint(1)')):
            with self.assertRaises(ValueError):
                render_response(data)

    def test_unknown_time_is_preserved_and_pipe_does_not_split_work_row(self):
        table = render_work_table([('未记录', '读取 A | B\n比较结果，耗时未知。')])
        self.assertIn('| 未记录 | 读取 A &#124; B 比较结果，耗时未知。 |', table)
        self.assertNotIn('<br', table)
        validate_response(render_response(self.report(work_process=table)))

    def test_work_table_is_body_content_with_facts_not_a_link_or_literal_example(self):
        for work in ('请打开附件查看工作过程。', '| 时间 | 工作 |\n| --- | --- |',
                     '```markdown\n| 时间 | 工作 |\n| --- | --- |\n| 未记录 | 阅读原件 |\n```'):
            with self.subTest(work=work):
                with self.assertRaisesRegex(ValueError, 'time/work table'):
                    render_response(self.report(work_process=work))
        table = '以下仅为选定事实，不代表全历史。\n\n时间／范围 | 对象 | 实际后果\n:--- | --- | ---:\n未单列 | 原件 A \\| B | 保留原结论\n'
        validate_response(render_response(self.report(work_process=table)))


if __name__ == '__main__':
    unittest.main()
