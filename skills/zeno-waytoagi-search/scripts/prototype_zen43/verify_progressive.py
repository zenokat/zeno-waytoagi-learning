"""不联网的原型行为核对：分页状态不漏候选、历史七天缓存、当月强制读取及共享摘要。

只替代外部 CLI 响应与当前日期；真实解析、月份缓存和续查状态仍由原型执行。
"""

from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from prototype import Prototype, daily
from monthly_logs import HISTORY_TTL_SECONDS, MonthlyLogs


def log_xml(month, tokens):
    """将 month 与 tokens 构造成日期日志 XML；返回保持真实引用格式的小样本。"""
    year, number = map(int, month.split("-"))
    rows = ''.join(f'<li>《<cite doc-id="{token}" file-type="wiki" title="{token}"/>》原摘要 {token}</li>' for token in tokens)
    return f'<h2>{year} 年 {number} 月</h2><h3>{number} 月 20 日</h3><ul>{rows}</ul>'


class ProgressiveChecks(unittest.TestCase):
    """使用小型外部响应验证真实工具入口的可观察行为。"""

    def setUp(self):
        """建立独立临时缓存、固定日期及外部 CLI 替身；无返回值。"""
        self.folder = tempfile.TemporaryDirectory(prefix="zen43-check-")
        self.addCleanup(self.folder.cleanup)
        self.anchor = json.loads(Path(__file__).with_name("monthly-fixtures.json").read_text())
        self.by_id = {v["block_id"]: k for k, v in self.anchor["months"].items()}
        self.requests = []
        self.clock = patch("monthly_logs.datetime")
        mocked = self.clock.start()
        self.date_clock = mocked
        mocked.now.return_value.date.return_value = date(2026, 10, 24)
        self.addCleanup(self.clock.stop)
        self.cli = patch.object(daily, "run_cli", side_effect=self.respond)
        self.cli.start()
        self.addCleanup(self.cli.stop)

    def respond(self, args):
        """按 args 返回文档或两页候选；第二页放入创建较早但十月收录的 late，返回 CLI 字典。"""
        self.requests.append(args)
        if args[:2] == ["drive", "+search"]:
            later = "--page-token" in args
            tokens = ["late"] if later else ["a", "b", "c", "d", "september"]
            return {"data": {"results": [{"result_meta": {"token": t, "url": "https://example.com/"+t},
                                          "summary_highlighted": "片段 "+t} for t in tokens],
                             "has_more": not later, "page_token": None if later else "next"}}
        block = args[args.index("--start-block-id") + 1]
        if block == self.anchor["recent"]["block_id"]:
            content = "<h1>近 7 日更新日志</h1>"
        else:
            month = self.by_id[block]
            tokens = ["a", "b", "c", "d", "late"] if month == "2026-10" else ["september"] if month == "2026-09" else []
            content = log_xml(month, tokens)
        return {"data": {"document": {"content": content, "revision_id": 1}}}

    def context(self):
        """返回共用测试缓存的新工具上下文，模拟新提交或新主题。"""
        return Prototype(self.folder.name)

    def test_progress_keeps_late_candidate_and_snippets(self):
        """首屏只取一页；本地续页后继续推进，较晚出现的十月文章不丢失、不重复。"""
        p = self.context()
        result = p.search(query="RAG")
        self.assertEqual(len(result["results"]), 3)
        self.assertEqual(p.diagnostics["native_pages"], 1)
        self.assertEqual(p.diagnostics["months_read"], ["2026-10"])
        found = list(result["results"])
        before = len(self.requests)
        result = self.context().search(cursor=result["next_cursor"])
        self.assertEqual(len(self.requests), before)
        found.extend(result["results"])
        for _ in range(25):
            if not result["next_cursor"]:
                break
            result = self.context().search(cursor=result["next_cursor"])
            found.extend(result["results"])
        self.assertIsNone(result["next_cursor"])
        self.assertEqual({r["article_id"] for r in found}, {"a", "b", "c", "d", "late", "september"})
        self.assertEqual(len(found), 6)
        self.assertTrue(all(r["snippet"].startswith("片段") for r in found))
        self.assertNotIn("coverage", result)

    def test_history_reused_across_topics_until_seven_days(self):
        """同月份跨主题复用且不查修订；第七天到期后只重新读该月。"""
        with patch("monthly_logs.time.time", return_value=1000000):
            self.context().search(query="RAG", since="2026-09-01", until="2026-09-30")
        docs_before = len([a for a in self.requests if a[:2] == ["docs", "+fetch"]])
        with patch("monthly_logs.time.time", return_value=1000000 + HISTORY_TTL_SECONDS - 1):
            self.context().search(query="Agent", since="2026-09-01", until="2026-09-30")
        self.assertEqual(len([a for a in self.requests if a[:2] == ["docs", "+fetch"]]), docs_before)
        with patch("monthly_logs.time.time", return_value=1000000 + HISTORY_TTL_SECONDS):
            self.context().search(since="2026-09-01", until="2026-09-30")
        self.assertEqual(len([a for a in self.requests if a[:2] == ["docs", "+fetch"]]), docs_before+1)
        self.assertTrue(all("outline" not in a and "full" not in a for a in self.requests))

    def test_current_always_requested_and_summaries_share_history(self):
        """当前月份跨调用必须请求；摘要找到指定文章后停止，历史月直接共用缓存。"""
        self.context().search(since="2026-09-01", until="2026-09-30")
        for _ in range(2):
            p = self.context()
            result = p.summaries(["a", "september"])
            self.assertEqual([r["summary"] for r in result["results"]], ["原摘要 a", "原摘要 september"])
            self.assertEqual([s["month"] for s in p.sources], ["2026-10", "2026-09"])
            self.assertEqual([s["cache_hit"] for s in p.sources], [False, True])
            self.assertEqual(len(p.calls), 2)

    def test_damaged_cache_is_refetched(self):
        """缓存损坏时重取目标月份，不将损坏当作有效空结果。"""
        logs = MonthlyLogs(self.context())
        logs.cache_path("2026-09").write_text('{"fetched_at":"bad","stable":true,"records":[]}')
        self.assertEqual(logs.read("2026-09")[0]["article_id"], "september")
        self.assertFalse(logs.context.sources[-1]["cache_hit"])

    def test_previous_month_stays_active_until_rollover_finishes(self):
        """月初上月仍读取近期页；滚动期后首次重取才写稳定缓存，避免冻结未归档月份。"""
        self.date_clock.now.return_value.date.return_value = date(2026, 10, 8)
        early = self.context()
        MonthlyLogs(early).read("2026-09")
        self.assertTrue(early.sources[0]["active"])
        self.assertEqual(len(early.calls), 2)
        self.date_clock.now.return_value.date.return_value = date(2026, 10, 9)
        settled = self.context()
        MonthlyLogs(settled).read("2026-09")
        self.assertFalse(settled.sources[0]["cache_hit"])
        self.assertEqual(len(settled.calls), 1)
        reused = self.context()
        MonthlyLogs(reused).read("2026-09")
        self.assertTrue(reused.sources[0]["cache_hit"])
        self.assertEqual(reused.calls, [])


if __name__ == "__main__":
    unittest.main()
