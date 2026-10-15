"""通过日期命令的公开入口验证统一更新读取，不访问真实账号或保存凭证。"""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "updates", Path(__file__).parents[1] / "skills/zeno-waytoagi-learning/scripts/waytoagi_daily.py",
)
UPDATES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UPDATES)


def cli_response(content, document_id):
    """将给定 XML 与文档标识包装为 CLI 成功响应，返回 JSON 字典。"""
    return {"ok": True, "identity": "user", "data": {"document": {
        "document_id": document_id, "content": content,
    }}}


def archive_responses():
    """提供近期页、年份路由与2025年单日原文样本，返回外部 CLI 响应表。"""
    entry = "https://waytoagi.feishu.cn/wiki/QPe5w5g7UisbEkkow8XcDmOpn8e"
    archive = "https://waytoagi.feishu.cn/wiki/FjiOwWp2giA7hRk6jjfcPioCnAc"
    older = "https://waytoagi.feishu.cn/wiki/year2025"
    return {
        (entry, "outline", None): cli_response('<fragment mode="outline"><h1 id="recent">近 7 日更新日志</h1></fragment>', UPDATES.SOURCE_DOCUMENT_ID),
        (entry, "section", "recent"): cli_response('<fragment mode="section" requested-start="recent"><h1 id="recent">近 7 日更新日志</h1><h3 id="today">10 月 14 日<ul><li id="now">《<cite doc-id="newArticle" file-type="wiki" title="近期文章"/>》近期摘要</li></ul></h3></fragment>', UPDATES.SOURCE_DOCUMENT_ID),
        (archive, "outline", None): cli_response('<fragment mode="outline"><h2 id="notice">温馨提示</h2><h2 id="month">2026 年 9 月</h2><h3 id="day">9 月 30 日</h3></fragment>', "archive2026"),
        (archive, "section", "notice"): cli_response('<fragment mode="section" requested-start="notice"><callout id="box"><h2 id="notice">温馨提示</h2><ul><li id="route">2025 年所有更新日志：<cite doc-id="year2025" file-type="wiki" title="2025 年历史更新（归档）"/></li></ul></callout></fragment>', "archive2026"),
        (older, "outline", None): cli_response('<fragment mode="outline"><h2 id="june">2025 年 6 月</h2><h3 id="old-day">6 月 1 日</h3></fragment>', "archive2025"),
        (older, "section", "old-day"): cli_response('<fragment mode="section" requested-start="old-day"><h3 id="old-day">6 月 1 日<ul><li id="old-entry">《<a href="https://example.com/original">历史文章</a>》原摘要：保留 标点。<br/>第二行</li></ul></h3></fragment>', "archive2025"),
    }


def run_date_command(day, responses, profile=None):
    """以来源样本运行真实日期命令；输入日期、CLI 响应表和可选配置，返回退出码及 JSON。

    只替代外部 CLI 进程，不替代脚本自己的定位与解析函数。
    """
    def external_cli(command, **kwargs):
        """根据实际只读 CLI 参数返回样本；输入 argv 与进程选项，返回进程结果。"""
        if command[:3] != ["lark-cli", "docs", "+fetch"] or command[command.index("--as") + 1] != "user":
            raise AssertionError("日期读取只能调用用户身份的 docs +fetch")
        if profile and command[command.index("--profile") + 1] != profile:
            raise AssertionError("命名配置必须贯穿所有页面读取")
        source = command[command.index("--doc") + 1]
        scope = command[command.index("--scope") + 1]
        anchor = command[command.index("--start-block-id") + 1] if "--start-block-id" in command else None
        result = responses[(source, scope, anchor)]
        code = 0 if result.get("ok") is True else 1
        payload = json.dumps(result)
        return subprocess.CompletedProcess(command, code, payload if not code else "", payload if code else "")

    arguments = ["waytoagi_daily.py", "--date", day]
    if profile:
        arguments += ["--profile", profile]
    output = io.StringIO()
    with patch.object(sys, "argv", arguments), \
            patch.object(UPDATES.subprocess, "run", side_effect=external_cli), \
            contextlib.redirect_stdout(output):
        code = UPDATES.main()
    return code, json.loads(output.getvalue())


class DateCommandTests(unittest.TestCase):
    """在命令行和 CLI 外部进程接口检查用户可观察的日期查询行为。"""

    def test_date_is_required_before_any_cli_request(self):
        """缺少 --date 时立即给出用法错误，不发起读取；无输入和返回值。"""
        with patch.object(sys, "argv", ["waytoagi_daily.py"]), \
                patch.object(UPDATES.subprocess, "run", side_effect=AssertionError("不应读取")), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                UPDATES.main()
        self.assertEqual(raised.exception.code, 2)

    def test_invalid_or_non_iso_dates_fail_without_reading(self):
        """不存在的日期及非 YYYY-MM-DD 输入给出用法错误；无返回值。"""
        for value in ["2026-02-29", "20250601", "2025/06/01"]:
            with self.subTest(value=value), \
                    patch.object(sys, "argv", ["waytoagi_daily.py", "--date", value]), \
                    patch.object(UPDATES.subprocess, "run", side_effect=AssertionError("不应读取")), \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    UPDATES.main()
                self.assertEqual(raised.exception.code, 2)

    def test_future_date_is_rejected_before_reading(self):
        """未来日期返回明确错误并避免读取来源；无输入和返回值。"""
        output = io.StringIO()
        with patch.object(sys, "argv", ["waytoagi_daily.py", "--date", "2999-01-01"]), \
                patch.object(UPDATES.subprocess, "run", side_effect=AssertionError("不应读取")), \
                contextlib.redirect_stdout(output):
            code = UPDATES.main()
        self.assertEqual(code, 2)
        self.assertIn("FUTURE_DATE", json.loads(output.getvalue())["error"])

    def test_dates_before_supported_start_do_not_read_any_page(self):
        """支持起点前一天及更早年份返回范围状态，不请求来源；无返回值。"""
        for day in ["2025-05-31", "2024-12-31", "2023-05-01"]:
            output = io.StringIO()
            with self.subTest(day=day), \
                    patch.object(sys, "argv", ["waytoagi_daily.py", "--date", day]), \
                    patch.object(UPDATES.subprocess, "run", side_effect=AssertionError("不应读取")), \
                    contextlib.redirect_stdout(output):
                code = UPDATES.main()
            result = json.loads(output.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(result["status"], "outside_supported_range")
            self.assertEqual(result["supported_from"], "2025-06-01")
            self.assertEqual(result["entries"], [])

    def test_date_query_follows_year_route_and_preserves_original_entry(self):
        """支持起点当天经年份链接得到原文与来源；无返回值。"""
        responses = archive_responses()

        code, result = run_date_command("2025-06-01", responses, "selected-profile")
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["target_date"], "2025-06-01")
        self.assertEqual(result["source_url"], "https://waytoagi.feishu.cn/wiki/year2025")
        self.assertEqual(result["entries"][0]["title"], "历史文章")
        self.assertEqual(result["entries"][0]["summary"], "原摘要：保留 标点。\n第二行")
        self.assertEqual(result["entries"][0]["links"][0]["url"], "https://example.com/original")

    def test_missing_year_route_is_a_failure_not_an_empty_date(self):
        """支持范围内的年份路由缺失时明确报错，不冒充该日没更新；无返回值。"""
        responses = archive_responses()
        intro = responses[(UPDATES.HISTORY_URL, "section", "notice")]["data"]["document"]
        intro["content"] = intro["content"].replace("2025", "2024")
        code, result = run_date_command("2025-06-01", responses)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "error")
        self.assertIn("ARCHIVE_YEAR_MISSING", result["error"])

    def test_recent_date_reads_only_the_matching_recent_batch(self):
        """近期命中时保持查询日期与原条目，不依赖归档；无返回值。"""
        responses = {key: value for key, value in archive_responses().items() if key[0] == UPDATES.SOURCE_URL}
        code, result = run_date_command("2026-10-14", responses)
        self.assertEqual(code, 0)
        self.assertEqual(result["target_date"], "2026-10-14")
        self.assertEqual(result["entries"][0]["title"], "近期文章")
        self.assertEqual(result["searched_sources"], [UPDATES.SOURCE_URL])

    def test_current_year_archive_reads_the_selected_date(self):
        """近期窗口外的当年日期直接定位年度归档；无返回值。"""
        responses = archive_responses()
        responses[(UPDATES.HISTORY_URL, "section", "day")] = cli_response(
            '<fragment mode="section" requested-start="day"><h3 id="day">9 月 30 日<ul><li id="entry">《<cite doc-id="archived" file-type="wiki" title="年度文章"/>》原文</li></ul></h3></fragment>',
            "archive2026",
        )
        code, result = run_date_command("2026-09-30", responses)
        self.assertEqual(code, 0)
        self.assertEqual(result["entries"][0]["title"], "年度文章")
        self.assertEqual(result["source_url"], UPDATES.HISTORY_URL)

    def test_same_month_day_uses_the_requested_year(self):
        """两个归档都有6月1日时，按实际年份取各自文章，不借请求日期改写来源年份。"""
        responses = archive_responses()
        responses[(UPDATES.HISTORY_URL, "outline", None)]["data"]["document"]["content"] = '<fragment mode="outline"><h2 id="notice">温馨提示</h2><h2 id="month">2026 年 6 月</h2><h3 id="day">6 月 1 日</h3></fragment>'
        responses[(UPDATES.HISTORY_URL, "section", "day")] = cli_response(
            '<fragment mode="section" requested-start="day"><h3 id="day">6 月 1 日<ul><li id="entry">《<cite doc-id="different" file-type="wiki" title="2026文章"/>》2026摘要</li></ul></h3></fragment>', "archive2026",
        )
        for target, title in [("2025-06-01", "历史文章"), ("2026-06-01", "2026文章")]:
            with self.subTest(target=target):
                code, result = run_date_command(target, responses)
                self.assertEqual(code, 0)
                self.assertEqual(result["target_date"], target)
                self.assertEqual(result["entries"][0]["title"], title)

    def test_year_end_and_new_year_dates_keep_their_archive_year(self):
        """年末与次年元旦分别读取对应年度来源；无返回值。"""
        responses = archive_responses()
        older = "https://waytoagi.feishu.cn/wiki/year2025"
        responses[(older, "outline", None)]["data"]["document"]["content"] = '<fragment mode="outline"><h2 id="month">2025 年 12 月</h2><h3 id="old-day">12 月 31 日</h3></fragment>'
        doc = responses[(older, "section", "old-day")]["data"]["document"]
        doc["content"] = doc["content"].replace("6 月 1 日", "12 月 31 日")
        responses[(UPDATES.HISTORY_URL, "outline", None)]["data"]["document"]["content"] = '<fragment mode="outline"><h2 id="notice">温馨提示</h2><h2 id="month">2026 年 1 月</h2><h3 id="day">1 月 1 日</h3></fragment>'
        responses[(UPDATES.HISTORY_URL, "section", "day")] = cli_response(
            '<fragment mode="section" requested-start="day"><h3 id="day">1 月 1 日<ul><li id="entry">《<cite doc-id="newYear" file-type="wiki" title="新年文章"/>》新年摘要</li></ul></h3></fragment>', "archive2026",
        )
        for target, source in [("2025-12-31", older), ("2026-01-01", UPDATES.HISTORY_URL)]:
            with self.subTest(target=target):
                code, result = run_date_command(target, responses)
                self.assertEqual(code, 0)
                self.assertEqual(result["target_date"], target)
                self.assertEqual(result["source_url"], source)

    def test_missing_date_does_not_substitute_another_batch(self):
        """完整查询未找到日期时返回独立状态和已检查来源，不换成其他日期；无返回值。"""
        code, result = run_date_command("2025-06-02", archive_responses())
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "date_batch_not_present")
        self.assertEqual(result["target_date"], "2025-06-02")
        self.assertEqual(result["entries"], [])
        self.assertIn("https://waytoagi.feishu.cn/wiki/year2025", result["searched_sources"])

    def test_duplicate_dates_do_not_return_an_arbitrary_batch(self):
        """同一归档出现重复目标日期时报告歧义；无返回值。"""
        responses = archive_responses()
        doc = responses[("https://waytoagi.feishu.cn/wiki/year2025", "outline", None)]["data"]["document"]
        doc["content"] = doc["content"].replace('</fragment>', '<h3 id="duplicate">6 月 1 日</h3></fragment>')
        code, result = run_date_command("2025-06-01", responses)
        self.assertEqual(code, 2)
        self.assertIn("AMBIGUOUS_DATE", result["error"])

    def test_invalid_archive_scope_source_or_content_is_not_success(self):
        """归档的节选、来源错配、日期错配、未知结构及空批次均明确失败；无返回值。"""
        source = "https://waytoagi.feishu.cn/wiki/year2025"
        cases = ["outline_tips", "section_excerpt", "wrong_document", "wrong_anchor", "wrong_date", "unknown_block", "empty_batch", "wrong_identity"]
        for case in cases:
            responses = archive_responses()
            outline = responses[(source, "outline", None)]["data"]["document"]
            section = responses[(source, "section", "old-day")]
            doc = section["data"]["document"]
            if case == "outline_tips":
                outline["tips"] = "仅有部分目录"
            elif case == "section_excerpt":
                doc["content"] = doc["content"].replace('<ul>', '<excerpt><ul>').replace('</ul>', '</ul></excerpt>')
            elif case == "wrong_document":
                doc["document_id"] = "another-document"
            elif case == "wrong_anchor":
                doc["content"] = doc["content"].replace('requested-start="old-day"', 'requested-start="other"')
            elif case == "wrong_date":
                doc["content"] = doc["content"].replace('6 月 1 日', '6 月 2 日')
            elif case == "unknown_block":
                doc["content"] = doc["content"].replace('</h3>', '<quote id="extra">新增结构</quote></h3>')
            elif case == "empty_batch":
                doc["content"] = '<fragment mode="section" requested-start="old-day"><h3 id="old-day">6 月 1 日</h3></fragment>'
            else:
                section["identity"] = "bot"
            with self.subTest(case=case):
                code, result = run_date_command("2025-06-01", responses)
                self.assertEqual(code, 2)
                self.assertEqual(result["status"], "error")
                self.assertNotIn("entries", result)

    def test_archive_authorization_error_keeps_its_reason(self):
        """归档权限失败仅报告原错误，不登录或换读取路线；无返回值。"""
        responses = archive_responses()
        responses[(UPDATES.HISTORY_URL, "outline", None)] = {
            "ok": False, "error": {"code": "NEED_USER_AUTHORIZATION", "message": "需要用户授权"},
        }
        code, result = run_date_command("2025-06-01", responses)
        self.assertEqual(code, 2)
        self.assertIn("NEED_USER_AUTHORIZATION", result["error"])

    def test_success_envelope_without_archive_data_is_a_structured_error(self):
        """CLI 成功信封缺少业务正文时返回错误JSON，不因空数据产生裸异常；无返回值。"""
        responses = archive_responses()
        responses[(UPDATES.HISTORY_URL, "outline", None)] = {"ok": True, "identity": "user", "data": None}
        code, result = run_date_command("2025-06-01", responses)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "error")
        self.assertIn("INVALID_RESPONSE", result["error"])


if __name__ == "__main__":
    unittest.main()
