"""对真实年度快照逐日回放日期命令；默认跳过，不持久保存第三方正文。

这项检查证明真实页面条目的完整解析与日期路由，不把回放当作逐日联网验收。
真实 CLI 的 section 行为另由 test_waytoagi_live.py 的日期抽样检查。
"""

from datetime import date
import json
import os
import re
import subprocess
import unittest
from xml.etree import ElementTree

from test_waytoagi_updates import cli_response, run_date_command


ENTRY = "https://waytoagi.feishu.cn/wiki/QPe5w5g7UisbEkkow8XcDmOpn8e"
HISTORY = "https://waytoagi.feishu.cn/wiki/FjiOwWp2giA7hRk6jjfcPioCnAc"
OLDER = "https://waytoagi.feishu.cn/wiki/GL7xwM3fyitr4kkiv76c1GHjnNg"


@unittest.skipUnless(os.environ.get("WAYTOAGI_LIVE") == "1", "需显式开启真实账号联网验收")
class ArchiveSnapshotTests(unittest.TestCase):
    """以真实年度页面为外部数据，逐日核对命令输出与原文条目集合。"""

    def read_cli(self, source, *extra):
        """读取给定公开来源与额外参数，返回用户身份的真实 CLI 响应，不回显失败正文。"""
        command = ["lark-cli", "docs", "+fetch", "--doc", source, "--as", "user", "--detail", "full", *extra]
        profile = os.environ.get("WAYTOAGI_PROFILE")
        if profile:
            command += ["--profile", profile]
        process = subprocess.run(command, capture_output=True, text=True, timeout=90)
        self.assertEqual(process.returncode, 0, "年度快照的只读 CLI 请求失败")
        response = json.loads(process.stdout)
        self.assertIs(response.get("ok"), True)
        self.assertEqual(response.get("identity"), "user")
        self.assertFalse(response["data"]["document"].get("tips"))
        return response

    def test_all_supported_archive_batches_preserve_original_entry_ids(self):
        """逐日回放2025-06-01起实际存在的批次，核对日期、来源与全部原条目ID。"""
        responses = {}
        for source in [ENTRY, HISTORY, OLDER]:
            responses[(source, "outline", None)] = self.read_cli(source, "--scope", "outline")
        recent_outline = ElementTree.fromstring(responses[(ENTRY, "outline", None)]["data"]["document"]["content"])
        recent_anchor = next(h.get("id") for h in recent_outline.iter("h1") if "近 7 日更新日志" in (h.text or ""))
        responses[(ENTRY, "section", recent_anchor)] = self.read_cli(ENTRY, "--scope", "section", "--start-block-id", recent_anchor)
        recent_root = ElementTree.fromstring(responses[(ENTRY, "section", recent_anchor)]["data"]["document"]["content"])
        recent_entries = {}
        for heading in recent_root.iter("h3"):
            match = re.match(r"\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", heading.text or "")
            if match:
                recent_entries[tuple(map(int, match.groups()))] = [entry.get("id") for entry in heading.iter("li")]
        outline = ElementTree.fromstring(responses[(HISTORY, "outline", None)]["data"]["document"]["content"])
        intro_anchor = next(h.get("id") for h in outline.iter("h2") if (h.text or "").strip() == "温馨提示")
        responses[(HISTORY, "section", intro_anchor)] = self.read_cli(HISTORY, "--scope", "section", "--start-block-id", intro_anchor)
        checked = 0
        for year, source in [(2025, OLDER), (2026, HISTORY)]:
            document = self.read_cli(source)["data"]["document"]
            root = ElementTree.fromstring("<root>" + document["content"] + "</root>")
            self.assertIsNone(root.find(".//excerpt"))
            for heading in root.iter("h3"):
                match = re.match(r"\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", heading.text or "")
                self.assertIsNotNone(match, "年度日期标题格式变化，须核对覆盖范围")
                target = date(year, *map(int, match.groups()))
                if target < date(2025, 6, 1):
                    continue
                self.assertRegex(heading.text or "", r"^\s*\d{1,2}\s*月\s*\d{1,2}\s*日\s*$")
                anchor = heading.get("id")
                # 真实整页里的日期子树作为 section 响应回放，保留原始 XML、标识和内容。
                fragment = ElementTree.Element("fragment", {"mode": "section", "requested-start": anchor})
                fragment.append(heading)
                responses[(source, "section", anchor)] = cli_response(
                    ElementTree.tostring(fragment, encoding="unicode"), document["document_id"],
                )
                with self.subTest(target=target.isoformat()):
                    code, result = run_date_command(target.isoformat(), responses, os.environ.get("WAYTOAGI_PROFILE"))
                    self.assertEqual(code, 0)
                    self.assertEqual(result["status"], "ok")
                    self.assertEqual(result["target_date"], target.isoformat())
                    self.assertIn(result["source_url"], [source, ENTRY])
                    expected_ids = recent_entries[(target.month, target.day)] if result["source_url"] == ENTRY else [entry.get("id") for entry in heading.iter("li")]
                    self.assertCountEqual(
                        [entry["source_block_id"] for entry in result["entries"]],
                        expected_ids,
                    )
                checked += 1
        self.assertGreater(checked, 400, "实际归档覆盖异常缩小，须重新核对来源")


if __name__ == "__main__":
    unittest.main()
