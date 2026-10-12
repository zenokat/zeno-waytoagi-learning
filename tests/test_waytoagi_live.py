"""通过真实飞书读取检查文档承诺，默认跳过，避免离线测试依赖网络与账号。

运行：WAYTOAGI_LIVE=1 python3 -m unittest discover -s tests -p test_waytoagi_live.py -v
可用 WAYTOAGI_PROFILE 指定已有配置；不登录、不创建应用、不保存响应或凭证。
断言检查结果内容和范围，而不只检查命令是否成功。来源改变时允许明确失败，
由维护者重新核对；不能用跳过或空结果掩盖已选择执行的联网验收失败。
"""

from datetime import date
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
from xml.etree import ElementTree


SKILL = Path(__file__).resolve().parents[1] / "skills" / "zeno-waytoagi"
SPACE_ID = "7226178700923011075"
ARTICLE = "https://waytoagi.feishu.cn/wiki/DyQPwr5Uui6n0HktnoxcYDrwngd"
HISTORY = "https://waytoagi.feishu.cn/wiki/FjiOwWp2giA7hRk6jjfcPioCnAc"


@unittest.skipUnless(os.environ.get("WAYTOAGI_LIVE") == "1", "需显式开启真实账号联网验收")
class WaytoagiLiveTests(unittest.TestCase):
    """验证更新、限定搜索、正文和扩展读取在同一已有账号下的实际结果。"""

    @classmethod
    def setUpClass(cls):
        """读取可选配置名并建立会话内结果缓存，无输入，无返回值。"""
        cls.profile = os.environ.get("WAYTOAGI_PROFILE")
        cls.cache = {}

    def run_json(self, command, success_field="ok"):
        """输入只读命令与成功字段名，检查退出码并返回 JSON；失败不回显完整响应。"""
        if self.profile:
            command = [*command, "--profile", self.profile]
        process = subprocess.run(command, capture_output=True, text=True, timeout=90)
        self.assertEqual(process.returncode, 0, f"只读命令退出码 {process.returncode}")
        response = json.loads(process.stdout)
        expected = "ok" if success_field == "status" else True
        self.assertEqual(response.get(success_field), expected)
        if success_field == "ok":
            self.assertEqual(response.get("identity"), "user")
        return response

    def search(self, *extra):
        """输入额外筛选参数，执行文档中的同库 ComfyUI 搜索，返回业务 data。"""
        return self.run_json([
            "lark-cli", "drive", "+search", "--query", "ComfyUI",
            "--space-ids", SPACE_ID, "--as", "user", "--page-size", "5",
            "--format", "json", *extra,
        ])["data"]

    def article(self, *extra):
        """输入范围或格式参数，读取已确认教程，返回正文字符串并拒绝带限制提示的响应。"""
        document = self.run_json([
            "lark-cli", "docs", "+fetch", "--doc", ARTICLE, "--as", "user", *extra,
        ])["data"]["document"]
        self.assertFalse(document.get("tips"), "读取出现限制，须重新核对文档承诺")
        content = document["content"]
        self.assertTrue(content.strip())
        return content

    def cached(self, name, load):
        """输入缓存名与读取函数，返回本轮读取结果，减少重复请求；不持久化数据。"""
        if name not in self.cache:
            self.cache[name] = load()
        return self.cache[name]

    def full_article(self):
        """无输入，返回文档中全篇 Markdown 读取命令的本轮实际正文。"""
        return self.cached("full", lambda: self.article("--doc-format", "markdown", "--detail", "simple"))

    def outline(self):
        """无输入，返回真实目录的 XML 元素，用实际块 ID 验证章节而不固定块位置。"""
        content = self.cached("outline", lambda: self.article("--scope", "outline", "--detail", "with-ids"))
        return ElementTree.fromstring(content)

    def latest(self):
        """无输入，执行包内每日命令并返回本轮最近更新批次 JSON。"""
        return self.cached("latest", lambda: self.run_json([
            sys.executable, str(SKILL / "scripts/waytoagi_daily.py"),
        ], "status"))

    def test_latest_update_has_original_material_and_actual_date(self):
        """最近批次必须完整，实际日期一致，且每条都有标题、摘要字段和真实链接。"""
        result = self.latest()
        self.assertTrue(result["scope_complete"])
        self.assertEqual(result["target_date"], result["available_dates"][0])
        self.assertLessEqual(date.fromisoformat(result["target_date"]), date.fromisoformat(result["fetched_at"][:10]))
        self.assertTrue(result["entries"])
        for entry in result["entries"]:
            self.assertTrue(entry["title"].strip())
            self.assertIsInstance(entry["summary"], str)
            self.assertTrue(entry["links"])
            for link in entry["links"]:
                self.assertRegex(link["url"], r"^https?://")

    def test_requested_date_returns_same_batch(self):
        """明确指定最近批次日期必须返回同批次原条目，不能换日或重写摘要。"""
        latest = self.latest()
        selected = self.run_json([
            sys.executable, str(SKILL / "scripts/waytoagi_daily.py"),
            "--date", latest["target_date"],
        ], "status")
        self.assertEqual(selected["target_date"], latest["target_date"])
        self.assertEqual(selected["entries"], latest["entries"])

    def test_search_returns_waytoagi_links_and_matching_context(self):
        """搜索必须返回限定知识库 URL、标题、摘要字段和实际关键词命中。"""
        results = self.cached("search", self.search)["results"]
        self.assertTrue(results)
        self.assertLessEqual(len(results), 5)
        for result in results:
            self.assertIn(f"visible_space_id={SPACE_ID}", result["result_meta"]["url"])
            self.assertTrue(result["title_highlighted"])
            self.assertIsInstance(result["summary_highlighted"], str)
            context = result["title_highlighted"] + result["summary_highlighted"]
            self.assertIn("comfyui", re.sub(r"<[^>]+>", "", context).lower())

    def test_search_pagination_returns_new_same_space_results(self):
        """第二页沿用响应令牌并取得不同结果，所有链接仍限定同一知识库。"""
        first = self.cached("search", self.search)
        self.assertTrue(first["has_more"], "验收主题已无第二页，需选择可翻页主题重验")
        self.assertTrue(first["page_token"])
        second = self.search("--page-token", first["page_token"])
        self.assertTrue(second["results"])
        first_urls = {item["result_meta"]["url"] for item in first["results"]}
        second_urls = {item["result_meta"]["url"] for item in second["results"]}
        self.assertTrue(second_urls - first_urls, "第二页没有新增结果")
        for url in second_urls:
            self.assertIn(f"visible_space_id={SPACE_ID}", url)

    def test_title_only_search_matches_every_title(self):
        """标题筛选必须有结果，且每个标题包含查询词，不以正文命中冒充标题命中。"""
        results = self.search("--only-title")["results"]
        self.assertTrue(results)
        for result in results:
            title = re.sub(r"<[^>]+>", "", result["title_highlighted"])
            self.assertIn("comfyui", title.lower())

    def test_full_article_contains_multiple_sections_and_body(self):
        """全文必须包含至少两个实际章节的正文，且不是目录、节选或局部响应。"""
        content = self.full_article()
        headings = list(self.outline().iter("h3"))
        self.assertGreaterEqual(len(headings), 2)
        for heading in headings[:2]:
            self.assertIn(heading.text.strip(), content)
        self.assertIn("自由和拓展", content)
        self.assertIn("KSampler", content)
        self.assertNotRegex(content, r"<excerpt|<fragment\b")

    def test_outline_returns_heading_ids(self):
        """目录明确标记 outline 范围，返回非空标题和可用于章节读取的实际 ID。"""
        outline = self.outline()
        self.assertEqual(outline.get("mode"), "outline")
        headings = list(outline.iter("h3"))
        self.assertGreaterEqual(len(headings), 2)
        for heading in headings:
            self.assertTrue(heading.get("id"))
            self.assertTrue(heading.text.strip())

    def test_section_returns_body_and_stops_before_next_peer(self):
        """按目录 ID 读取第一节正文，范围标记正确，且不包含第二个同级标题。"""
        first, second = list(self.outline().iter("h3"))[:2]
        content = self.article(
            "--scope", "section", "--start-block-id", first.get("id"),
            "--doc-format", "markdown", "--detail", "simple",
        )
        self.assertIn('mode="section"', content)
        self.assertIn(f'requested-start="{first.get("id")}"', content)
        self.assertIn(first.text.strip(), content)
        self.assertIn("自由和拓展", content)
        self.assertNotIn(second.text.strip(), content)
        self.assertLess(len(content), len(self.full_article()))

    def test_keyword_returns_matching_local_context(self):
        """关键词返回标记为 keyword 的实际命中与上下文，长度小于全篇。"""
        content = self.article(
            "--scope", "keyword", "--keyword", "KSampler",
            "--doc-format", "markdown", "--detail", "simple",
        )
        self.assertIn('mode="keyword"', content)
        self.assertRegex(content, r'hit-block-ids="[^"]+"')
        self.assertIn("KSampler", content)
        self.assertIn("采样器", content)
        self.assertLess(len(content), len(self.full_article()))

    def test_keyword_context_can_expand_via_outline_section(self):
        """关键词上下文不足时，用目录中的相关标题 ID 继续读章节，避免把普通命中块当标题。"""
        keyword = self.article(
            "--scope", "keyword", "--keyword", "KSampler",
            "--doc-format", "markdown", "--detail", "simple",
        )
        self.assertIn("KSampler", keyword)
        # 关键词可能命中普通段落；section 需要标题，因此从真实目录取得标题 ID。
        headings = [item for item in self.outline().iter() if item.tag.startswith("h") and (item.text or "").strip() == "KSampler"]
        self.assertEqual(len(headings), 1, "验收教程的关键词章节无法唯一定位，需重新核对")
        anchor = headings[0].get("id")
        self.assertTrue(anchor)
        section = self.article(
            "--scope", "section", "--start-block-id", anchor,
            "--doc-format", "markdown", "--detail", "simple",
        )
        self.assertIn('mode="section"', section)
        self.assertIn("KSampler", section)
        self.assertIn("采样器", section)

    def test_historical_update_page_returns_older_dated_entries(self):
        """历史页定位窗口之前的日期，并读到该日原摘要和文档引用，非仅 URL 可打开。"""
        document = self.run_json([
            "lark-cli", "docs", "+fetch", "--doc", HISTORY,
            "--as", "user", "--scope", "outline", "--detail", "with-ids",
        ])["data"]["document"]
        tree = ElementTree.fromstring(document["content"])
        cutoff = date.fromisoformat(self.latest()["available_dates"][-1])
        year = None
        selected = None
        for heading in tree.iter():
            text = heading.text or ""
            month_heading = re.fullmatch(r"\s*(\d{4})\s*年\s*\d{1,2}\s*月\s*", text)
            if month_heading:
                year = int(month_heading.group(1))
            day_heading = re.match(r"\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
            if year and day_heading and date(year, *map(int, day_heading.groups())) < cutoff:
                selected = heading
                break
        self.assertIsNotNone(selected, "历史页没有可验证的旧日期标题")
        section = self.run_json([
            "lark-cli", "docs", "+fetch", "--doc", HISTORY, "--as", "user",
            "--scope", "section", "--start-block-id", selected.get("id"), "--detail", "full",
        ])["data"]["document"]
        self.assertFalse(section.get("tips"))
        content = ElementTree.fromstring(section["content"])
        self.assertEqual(content.get("mode"), "section")
        self.assertEqual(content.get("requested-start"), selected.get("id"))
        self.assertIsNone(content.find(".//excerpt"))
        references = list(content.iter("cite"))
        self.assertTrue(references, "没有取得历史条目的原文引用")
        for reference in references:
            self.assertTrue(reference.get("title"))
            self.assertTrue(reference.get("doc-id") or reference.get("url"))
        self.assertGreater(len("".join(content.itertext()).strip()), 80, "没有取得历史原摘要")


if __name__ == "__main__":
    unittest.main()
