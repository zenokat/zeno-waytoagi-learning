"""验证 CLI 每日获取的日期覆盖、引用链接、原摘要及失败语义，不保存凭证。"""

import contextlib
from datetime import date
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.sax.saxutils import escape
from zoneinfo import TZPATH


SPEC = importlib.util.spec_from_file_location("waytoagi_daily", Path(__file__).parents[1] / "skills" / "zeno-waytoagi-learning" / "scripts" / "waytoagi_daily.py")
DAILY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DAILY)


def document_with_batches(labels, fetched_at="2026-09-06T01:00:00+00:00"):
    """按输入日期标题生成带原摘要和真实形状链接的独立测试文档，返回 dict。"""
    blocks = [{"id": "section", "type": "heading1", "depth": 1, "text": DAILY.SECTION, "links": []}]
    for index, label in enumerate(labels):
        blocks.extend([
            {"id": f"day-{index}", "type": "heading3", "depth": 1, "text": label, "links": []},
            {"id": f"entry-{index}", "type": "bullet", "depth": 2, "text": "《示例文章》原摘要：保留标点与 换行。\n下一行", "links": [{"title": "示例文章", "url": "https://example.com/article", "kind": "mention_doc"}]},
        ])
    return {"status": "ok", "source_url": DAILY.SOURCE_URL, "fetched_at": fetched_at, "scope_complete": True, "blocks": blocks}


def cli_response_with_batches(labels, fetched_at="2026-09-06T01:00:00+00:00"):
    """生成 CLI section 响应样本；输入日期标签和抓取时间，返回带引用的 JSON 对象。"""
    batches = []
    for index, label in enumerate(labels):
        batches.append(
            f'<h3 id="day-{index}">{escape(label)}<ul><li id="entry-{index}">'
            '《<cite doc-id="articleToken" file-type="wiki" title="示例文章"/>》'
            '原摘要：保留标点与 换行。<br/>下一行</li></ul></h3>'
        )
    return {
        "ok": True, "identity": "user", "fetched_at": fetched_at,
        "data": {"document": {
            "document_id": DAILY.SOURCE_DOCUMENT_ID, "revision_id": 10,
            "content": '<fragment mode="section" requested-start="section">'
            f'<h1 id="section">{DAILY.SECTION}</h1><p id="intro">查看所有更新日志</p>'
            + "".join(batches) + '</fragment>',
        }},
    }


class CliReadingTests(unittest.TestCase):
    """验证真实 CLI 结构能提取原始材料，权限及结构错误不能冒充空更新。"""

    def test_nested_heading_and_document_reference_are_preserved(self):
        """CLI 日期标题包裹条目时仍保留标题、逐字摘要、链接和原块标识。"""
        response = cli_response_with_batches(["9 月 5 日", "9 月 4 日"])
        document = DAILY.document_from_cli(response, response["fetched_at"])
        result = DAILY.extract_daily(document, date(2026, 9, 5))
        self.assertEqual(result["target_date"], "2026-09-05")
        self.assertEqual(result["entries"][0]["title"], "示例文章")
        self.assertEqual(result["entries"][0]["summary"], "原摘要：保留标点与 换行。\n下一行")
        self.assertEqual(result["entries"][0]["links"][0]["url"], "https://waytoagi.feishu.cn/wiki/articleToken")
        self.assertEqual(result["entries"][0]["source_block_id"], "entry-0")

    def test_actual_external_link_and_inline_formatting_are_preserved(self):
        """外部链接和行内强调不丢失，原 URL 不被改写为飞书链接。"""
        response = cli_response_with_batches(["9 月 5 日"])
        response["data"]["document"]["content"] = response["data"]["document"]["content"].replace(
            '<cite doc-id="articleToken" file-type="wiki" title="示例文章"/>',
            '<a href="https://example.com/article?x=1&amp;y=2"><b>示例文章</b></a>',
        )
        document = DAILY.document_from_cli(response, response["fetched_at"])
        entry = DAILY.extract_daily(document, date(2026, 9, 5))["entries"][0]
        self.assertEqual(entry["title"], "示例文章")
        self.assertEqual(entry["links"][0]["url"], "https://example.com/article?x=1&y=2")

    def test_visual_separators_do_not_hide_entries(self):
        """真实板块中的横线和图片不变成条目，也不截断后面的原始材料。"""
        response = cli_response_with_batches(["9 月 5 日"])
        response["data"]["document"]["content"] = response["data"]["document"]["content"].replace(
            '</h3>', '<hr id="divider"/><img id="image" alt="图片说明"/><ul>'
            '<li id="second">《<cite doc-id="secondToken" file-type="wiki" title="第二篇"/>》第二条摘要</li>'
            '</ul></h3>',
        )
        document = DAILY.document_from_cli(response, response["fetched_at"])
        result = DAILY.extract_daily(document, date(2026, 9, 5))
        self.assertEqual([entry["title"] for entry in result["entries"]], ["示例文章", "第二篇"])
        self.assertEqual(result["skipped_image_blocks"], 1)

    def test_partial_or_wrong_scope_response_fails(self):
        """节选、目录和截断响应不能被当作完整的每日板块。"""
        for replacement in ('<excerpt>', '<fragment mode="outline">', '<fragment mode="section">'):
            with self.subTest(replacement=replacement):
                response = cli_response_with_batches(["9 月 5 日"])
                content = response["data"]["document"]["content"]
                if replacement == '<excerpt>':
                    content = content.replace('<ul>', '<excerpt><ul>').replace('</ul>', '</ul></excerpt>')
                elif 'outline' in replacement:
                    content = content.replace('mode="section"', 'mode="outline"')
                else:
                    content = content[:-11]
                response["data"]["document"]["content"] = content
                with self.assertRaises(ValueError):
                    DAILY.document_from_cli(response, response["fetched_at"])

    def test_missing_reference_title_or_token_fails(self):
        """无法还原标题或实际文档地址的引用明确失败，不生成占位链接。"""
        for attribute in ('title="示例文章"', 'doc-id="articleToken"'):
            with self.subTest(attribute=attribute):
                response = cli_response_with_batches(["9 月 5 日"])
                response["data"]["document"]["content"] = response["data"]["document"]["content"].replace(attribute, '')
                with self.assertRaises(ValueError):
                    DAILY.document_from_cli(response, response["fetched_at"])

    def test_unknown_nested_inline_content_is_not_silently_dropped(self):
        """行内嵌套出现未支持的内容时明确失败，不能丢失文字后仍报告完整。"""
        response = cli_response_with_batches(["9 月 5 日"])
        response["data"]["document"]["content"] = response["data"]["document"]["content"].replace(
            '下一行', '<span><unknown>下一行</unknown></span>',
        )
        with self.assertRaisesRegex(ValueError, "ENTRY_FORMAT_CHANGED"):
            DAILY.document_from_cli(response, response["fetched_at"])

    def test_missing_document_response_is_structured_failure(self):
        """上游返回空文档时使用可处理的失败状态，不产生未捕获异常。"""
        response = cli_response_with_batches(["9 月 5 日"])
        response["data"]["document"] = None
        with self.assertRaisesRegex(ValueError, "INVALID_RESPONSE"):
            DAILY.document_from_cli(response, response["fetched_at"])

    def test_authorization_failure_does_not_start_login_or_anonymous_fallback(self):
        """CLI 授权失败仅返回明确原因，不调用登录命令或其他读取路线。"""
        failed = subprocess.CompletedProcess([], 1, '', json.dumps({
            "ok": False, "error": {"code": "NEED_USER_AUTHORIZATION", "message": "需要用户重新授权"},
        }))
        with patch.object(DAILY.subprocess, "run", return_value=failed) as run:
            with self.assertRaisesRegex(ValueError, "NEED_USER_AUTHORIZATION"):
                DAILY.fetch_cli_section()
        self.assertEqual(run.call_count, 1)

    def test_refresh_diagnostic_does_not_hide_authorization_error(self):
        """CLI 先输出续期诊断再输出错误 JSON 时，仍保留需要重新授权的原因。"""
        stderr = '[lark-cli] uat-client: refresh_token expired, clearing\n' + json.dumps({
            "ok": False, "error": {"code": "NEED_USER_AUTHORIZATION", "message": "需要重新授权"},
        })
        with patch.object(DAILY.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, '', stderr)):
            with self.assertRaisesRegex(ValueError, "NEED_USER_AUTHORIZATION"):
                DAILY.fetch_cli_section()

    def test_profile_is_forwarded_to_both_read_requests(self):
        """指定命名配置时，目录定位与板块读取两次 CLI 调用都携带同一 --profile。"""
        outline = {"ok": True, "identity": "user", "data": {"document": {
            "document_id": DAILY.SOURCE_DOCUMENT_ID,
            "content": '<fragment mode="outline"><h1 id="sec">近 7 日更新日志</h1></fragment>',
        }}}
        section = cli_response_with_batches(["9 月 5 日"])
        responses = [
            subprocess.CompletedProcess([], 0, json.dumps(outline), ''),
            subprocess.CompletedProcess([], 0, json.dumps(section), ''),
        ]
        with patch.object(DAILY.subprocess, "run", side_effect=responses) as run:
            DAILY.fetch_cli_section("waytoagi-verify")
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            argv = call.args[0]
            self.assertEqual(argv[argv.index("--profile") + 1], "waytoagi-verify")

    def test_default_profile_does_not_add_profile_flag(self):
        """未指定命名配置时不向 CLI 传 --profile，保持默认配置的既有行为。"""
        outline = {"ok": True, "identity": "user", "data": {"document": {
            "document_id": DAILY.SOURCE_DOCUMENT_ID,
            "content": '<fragment mode="outline"><h1 id="sec">近 7 日更新日志</h1></fragment>',
        }}}
        section = cli_response_with_batches(["9 月 5 日"])
        responses = [
            subprocess.CompletedProcess([], 0, json.dumps(outline), ''),
            subprocess.CompletedProcess([], 0, json.dumps(section), ''),
        ]
        with patch.object(DAILY.subprocess, "run", side_effect=responses) as run:
            DAILY.fetch_cli_section()
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            self.assertNotIn("--profile", call.args[0])


class DailyFailureTests(unittest.TestCase):
    """验证用户环境和官方 CLI 失败时，实际命令仍给出可诊断结果，不暗中改变身份。"""

    def assert_cli_failure(self, outcome, expected_reason):
        """输入 CLI 返回值或异常及预期原因，执行 main 并验证失败 JSON；无返回值。"""
        behavior = {"side_effect": outcome} if isinstance(outcome, Exception) else {"return_value": outcome}
        output = io.StringIO()
        with patch.object(DAILY.subprocess, "run", **behavior) as run, \
                patch.object(sys, "argv", ["waytoagi_daily.py", "--date", "2026-09-05", "--profile", "test-profile"]), \
                contextlib.redirect_stdout(output):
            self.assertEqual(DAILY.main(), 2)
        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "error")
        self.assertIn(expected_reason, result["error"])
        self.assertNotIn("entries", result)
        self.assertEqual(run.call_count, 1, "失败后不能自动登录、换配置或尝试匿名抓取")
        arguments = run.call_args.args[0]
        self.assertEqual(arguments[arguments.index("--profile") + 1], "test-profile")
        self.assertEqual(arguments[arguments.index("--as") + 1], "user")

    def test_missing_cli_has_actionable_failure(self):
        """找不到官方 CLI 时返回明确依赖错误，而不是安装过程中无法理解的裸异常。"""
        self.assert_cli_failure(FileNotFoundError(2, "No such file or directory", "lark-cli"), "CLI_NOT_FOUND")

    def test_timeout_is_reported_without_extra_requests(self):
        """读取超时返回稳定原因和失败状态，脚本自身不无限重试。"""
        self.assert_cli_failure(subprocess.TimeoutExpired(["lark-cli"], 90), "CLI_TIMEOUT")

    def test_service_failures_keep_reason_and_missing_scopes(self):
        """模拟授权、缺权限、资源拒绝、限流及凭证存储错误，保留诊断并停止读取。"""
        failures = [
            ({"code": "NEED_USER_AUTHORIZATION", "message": "需要用户授权"}, "NEED_USER_AUTHORIZATION"),
            ({"message": "缺少读取权限", "missing_scopes": ["docs:document.content:read"]}, "docs:document.content:read"),
            ({"code": 131006, "message": "资源访问被拒绝"}, "131006"),
            ({"code": 429, "message": "模拟限流"}, "429"),
            ({"type": "internal", "subtype": "storage", "message": "keychain Get failed"}, "keychain Get failed"),
        ]
        for error, expected in failures:
            with self.subTest(reason=expected):
                response = subprocess.CompletedProcess([], 1, "", json.dumps({"ok": False, "error": error}))
                self.assert_cli_failure(response, expected)

    def test_non_json_diagnostics_are_not_exposed(self):
        """CLI 输出未知格式时明确失败，不将可能含敏感信息的原始诊断回显给用户。"""
        diagnostic = "SIMULATED_SENSITIVE_DIAGNOSTIC"
        response = subprocess.CompletedProcess([], 1, "", diagnostic)
        output = io.StringIO()
        with patch.object(DAILY.subprocess, "run", return_value=response), \
                patch.object(sys, "argv", ["waytoagi_daily.py", "--date", "2026-09-05"]), contextlib.redirect_stdout(output):
            self.assertEqual(DAILY.main(), 2)
        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "error")
        self.assertIn("CLI_FAILED", result["error"])
        self.assertNotIn(diagnostic, output.getvalue())

    def test_missing_timezone_data_returns_json_without_cli(self):
        """真实新进程缺少时区库时，仍返回可修复的 JSON，不在模块导入时崩溃。"""
        with tempfile.TemporaryDirectory() as empty_data:
            environment = {**os.environ, "PYTHONTZPATH": empty_data}
            # -S 排除已安装的 tzdata，空 PYTHONTZPATH 排除系统库，模拟新机器缺依赖。
            process = subprocess.run(
                [sys.executable, "-S", str(Path(DAILY.__file__)), "--date", "2026-09-05"], env=environment,
                capture_output=True, text=True, timeout=10,
            )
        self.assertEqual(process.returncode, 2)
        result = json.loads(process.stdout)
        self.assertEqual(result["status"], "error")
        self.assertIn("TIMEZONE_DATA_MISSING", result["error"])
        self.assertIn("tzdata", result["error"])
        self.assertNotIn("Traceback", process.stderr)

    def test_restoring_timezone_data_recovers_in_the_same_python(self):
        """同一解释器缺时区先失败，补回新加坡数据后成功，日期仍按来源时区解释。"""
        timezone_file = next((Path(root) / "Asia/Singapore" for root in TZPATH
                              if (Path(root) / "Asia/Singapore").is_file()), None)
        self.assertIsNotNone(timezone_file, "此恢复验收需要现有系统时区文件作为外部输入")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "section.json"
            source.write_text(json.dumps(cli_response_with_batches(["9 月 5 日"])))
            environment = {**os.environ, "PYTHONTZPATH": str(root / "timezone")}
            command = [sys.executable, "-S", str(Path(DAILY.__file__)), "--date", "2026-09-05", "--input", str(source)]
            missing = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
            self.assertEqual(missing.returncode, 2)
            self.assertIn("TIMEZONE_DATA_MISSING", json.loads(missing.stdout)["error"])
            target = root / "timezone/Asia/Singapore"
            target.parent.mkdir(parents=True)
            target.write_bytes(timezone_file.read_bytes())
            restored = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(restored.returncode, 0)
        result = json.loads(restored.stdout)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["timezone"], "Asia/Singapore")
        self.assertEqual(result["target_date"], "2026-09-05")


class DailyExtractionTests(unittest.TestCase):
    """覆盖实际用户可观察行为，防止空结果、日期错配与摘要改写。"""

    def test_requested_recent_date_returns_original_batch(self):
        """指定近期日期时取得该日原始条目和实际日期。"""
        result = DAILY.extract_daily(document_with_batches(["9 月 5 日", "9 月 4 日"]), date(2026, 9, 5))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["target_date"], "2026-09-05")
        self.assertEqual(result["entries"][0]["source_block_id"], "entry-0")

    def test_requested_year_end_batch_keeps_previous_year(self):
        """新年请求前一天批次时，年末批次仍使用原来的年份。"""
        result = DAILY.extract_daily(document_with_batches(["12 月 31 日", "12 月 30 日"], "2026-12-31T17:00:00Z"), date(2026, 12, 31))
        self.assertEqual(result["target_date"], "2026-12-31")

    def test_requested_empty_batch_does_not_fall_back(self):
        """指定标题下缺少条目时显式失败，不以更旧批次掩盖提取异常。"""
        document = document_with_batches(["9 月 5 日", "9 月 4 日"])
        document["blocks"].pop(2)
        with self.assertRaisesRegex(ValueError, "EMPTY_BATCH"):
            DAILY.extract_daily(document, date(2026, 9, 5))

    def test_command_reads_requested_date_and_reports_source_errors(self):
        """实际命令按必填日期取批次；不完整输入仍返回结构化错误和失败退出码。"""
        for complete in (True, False):
            with self.subTest(complete=complete), tempfile.TemporaryDirectory() as directory:
                response = cli_response_with_batches(["9 月 5 日", "9 月 4 日"])
                if not complete:
                    response["data"]["document"]["content"] = response["data"]["document"]["content"][:-11]
                source = Path(directory) / "cli-section.json"
                source.write_text(json.dumps(response))
                process = subprocess.run([sys.executable, "-B", str(Path(DAILY.__file__)), "--date", "2026-09-05", "--input", str(source)], capture_output=True, text=True, check=False)
                result = json.loads(process.stdout)
                self.assertEqual(process.returncode, 0 if complete else 2)
                self.assertEqual(result["status"], "ok" if complete else "error")
                self.assertEqual(result["target_date"], "2026-09-05")

    def test_command_profile_argument_reaches_cli_fetch(self):
        """命令行 --profile 传入的命名配置名原样到达在线读取，离线 --input 模式不触发 CLI。"""
        document = DAILY.document_from_cli(cli_response_with_batches(["9 月 5 日"]), "2026-09-06T01:00:00+00:00")
        with patch.object(DAILY, "fetch_cli_section", return_value=document) as fetch, \
                patch.object(sys, "argv", ["waytoagi_daily.py", "--date", "2026-09-05", "--profile", "waytoagi-verify"]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(DAILY.main(), 0)
        fetch.assert_called_once_with("waytoagi-verify")

    def test_retains_summary_and_only_requested_day(self):
        """指定一天时只返回该天条目，并逐字保留标题后原摘要及链接。"""
        result = DAILY.extract_daily(document_with_batches(["9 月 5 日", "9 月 4 日"]), date(2026, 9, 4))
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["entries"][0]["source_block_id"], "entry-1")
        self.assertEqual(result["entries"][0]["summary"], "原摘要：保留标点与 换行。\n下一行")
        self.assertEqual(result["entries"][0]["links"][0]["url"], "https://example.com/article")

    def test_current_batch_absent_is_explicit(self):
        """当天标题未出现时返回独立状态，并给出最新可用日期。"""
        result = DAILY.extract_daily(document_with_batches(["9 月 5 日"]), date(2026, 9, 6))
        self.assertEqual(result["status"], "date_batch_not_present")
        self.assertEqual(result["latest_available_date"], "2026-09-05")

    def test_old_request_does_not_relabel_current_articles(self):
        """旧日期请求不得改变当年标题的年份，应识别为超出公开窗口。"""
        result = DAILY.extract_daily(document_with_batches(["9 月 5 日"]), date(2025, 9, 5))
        self.assertEqual(result["status"], "outside_available_window")

    def test_year_rollover_uses_singapore_date(self):
        """UTC 年末但新加坡已跨年时，1 月批次属新年，12 月批次属上一年。"""
        result = DAILY.extract_daily(document_with_batches(["1 月 1 日", "12 月 31 日"], "2026-12-31T17:00:00Z"), date(2026, 12, 31))
        self.assertEqual(result["available_dates"], ["2027-01-01", "2026-12-31"])

    def test_partial_source_fails(self):
        """范围不完整时必须失败，不能返回目标日期没有更新。"""
        document = document_with_batches(["9 月 5 日"])
        document["scope_complete"] = False
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_SOURCE"):
            DAILY.extract_daily(document, date(2026, 9, 6))

    def test_missing_links_fail(self):
        """未取得实际链接的条目必须失败，不能生成占位 URL。"""
        document = document_with_batches(["9 月 5 日"])
        document["blocks"][-1]["links"] = []
        with self.assertRaisesRegex(ValueError, "ENTRY_FORMAT_CHANGED"):
            DAILY.extract_daily(document, date(2026, 9, 5))

    def test_empty_existing_batch_fails(self):
        """日期标题存在但条目为空时，视为提取异常而非确认无更新。"""
        document = document_with_batches(["9 月 5 日"])
        document["blocks"].pop()
        with self.assertRaisesRegex(ValueError, "EMPTY_BATCH"):
            DAILY.extract_daily(document, date(2026, 9, 5))

    def test_duplicate_dates_fail(self):
        """重复日期必须显式报错，避免静默遗漏其中一批条目。"""
        with self.assertRaisesRegex(ValueError, "INVALID_DATE_ORDER"):
            DAILY.extract_daily(document_with_batches(["9 月 5 日", "9 月 5 日"]), date(2026, 9, 5))

    def test_wrong_section_fails(self):
        """同来源的其他板块不能冒充近 7 日更新日志。"""
        document = document_with_batches(["9 月 5 日"])
        document["blocks"][0]["text"] = "历史精选"
        with self.assertRaisesRegex(ValueError, "WRONG_SECTION"):
            DAILY.extract_daily(document, date(2026, 9, 5))

    def test_nested_date_heading_fails(self):
        """嵌套日期形式的子标题不能被误认为另一天的批次。"""
        document = document_with_batches(["9 月 5 日"])
        document["blocks"].insert(2, {"id": "nested", "type": "heading4", "depth": 2, "text": "9 月 4 日", "links": []})
        with self.assertRaisesRegex(ValueError, "DATE_STRUCTURE_CHANGED"):
            DAILY.extract_daily(document, date(2026, 9, 4))

    def test_unknown_same_level_heading_fails(self):
        """日期内新出现非日期同级标题时须报错，不能静默截断剩余条目。"""
        document = document_with_batches(["9 月 5 日"])
        document["blocks"].append({"id": "extra", "type": "heading3", "depth": 1, "text": "补充阅读", "links": []})
        with self.assertRaisesRegex(ValueError, "DATE_STRUCTURE_CHANGED"):
            DAILY.extract_daily(document, date(2026, 9, 5))

    def test_unknown_nonempty_block_fails(self):
        """不支持的非空文字块不能无声丢弃后仍声称批次完整。"""
        document = document_with_batches(["9 月 5 日"])
        document["blocks"].append({"id": "extra", "type": "quote", "depth": 2, "text": "新增条目", "links": []})
        with self.assertRaisesRegex(ValueError, "ENTRY_FORMAT_CHANGED"):
            DAILY.extract_daily(document, date(2026, 9, 5))


if __name__ == "__main__":
    unittest.main()
