"""ZEN-43 可丢弃技术原型：五个工具的真实只读 lark-cli 组合。

复用相邻 daily 脚本的 CLI 校验和行内文字解析；仅依赖 Python 标准库。
缓存、去评论后的原生响应、正文和图片只写入执行环境临时目录。
本文件验证主要路径，不是已发布接口；异常产品规则由 ZEN-44 决定。
"""

import argparse
import copy
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import waytoagi_daily as daily

SPACE = "7226178700923011075"
SAMPLE = "https://waytoagi.feishu.cn/wiki/HwMqw2TTpirl1Ykh5MhcfMEXnxd"
PARSER_VERSION = 2


def write_json(path, value):
    """把 value 写入 path 指定的 UTF-8 JSON 文件；返回绝对路径，写入失败直接报错。"""
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def xml_root(content):
    """把 CLI 的多根 XML 字符串 content 包为根节点；返回可遍历树，解析失败报错。"""
    root = ET.fromstring("<root>" + content + "</root>")
    if len(root) == 1 and root[0].tag == "fragment":
        return root[0]
    return root


def strip_comments(response):
    """原地剥除 response 中评论 sidecar、评论正文和锚点；返回剥除数量，不保留评论文本。"""
    count = 0
    document = response.get("data", {}).get("document", {})
    references = document.get("reference_map", {})
    removed = references.pop("comments", {})
    count += len(removed)
    content = document.get("content", "")
    content, n = re.subn(r"<comment\b[^>]*>.*?</comment>", "", content, flags=re.S)
    count += n
    content = re.sub(r"</?(?:comment-ref|comment-anchor|comment-start|comment-end)\b[^>]*>", "", content)
    content = re.sub(r'\s+comment(?:-ids?|-refs?)="[^"]*"', "", content)
    document["content"] = content
    return count


def top_blocks(root):
    """从 root 还原文档顶层块序列；展开标题包装与列表包装，保留表格等完整容器。"""
    blocks = []
    for element in root:
        if element.tag in {"ul", "ol"}:
            blocks.extend(top_blocks(element))
        elif re.fullmatch(r"h[1-6]", element.tag):
            heading = copy.deepcopy(element)
            for child in list(heading):
                if child.tag not in daily.INLINE_TAGS:
                    heading.remove(child)
            blocks.append(heading)
            wrapper = ET.Element("root")
            wrapper.extend(child for child in element if child.tag not in daily.INLINE_TAGS)
            blocks.extend(top_blocks(wrapper))
        elif element.tag != "title":
            blocks.append(element)
    return blocks


def section_model(content):
    """由完整 content 建立顶层块、实际章节树和块归属；返回 blocks、units、positions 三元组。"""
    blocks = top_blocks(xml_root(content))
    units, stack, positions = [], [], {}
    for index, block in enumerate(blocks):
        for nested in block.iter():
            if nested.get("id"):
                positions[nested.get("id")] = index
        if not re.fullmatch(r"h[1-6]", block.tag):
            continue
        rank = int(block.tag[1:])
        while stack and stack[-1]["rank"] >= rank:
            stack.pop()["end"] = index
        unit = {"id": block.get("id"), "title": daily.inline_content(block)[0],
                "rank": rank, "depth": len(stack) + 1, "start": index, "end": len(blocks),
                "parents": [ancestor["id"] for ancestor in stack], "kind": "section"}
        units.append(unit)
        stack.append(unit)
    first = units[0]["start"] if units else len(blocks)
    if first:
        units.insert(0, {"id": "@opening" if units else "@document", "title": "开篇正文" if units else "全文（无标题）",
                         "depth": 1, "parents": [], "start": 0, "end": first, "kind": "reading_unit"})
    return blocks, units, positions


def log_entries(content, source, current_day):
    """从日志 content 按日期标题和引用关联原摘要；输入来源与当天日期，返回记录、未解析项、年份路由。"""
    root = xml_root(content)
    year, batch = None, None
    records, unsupported, routes = [], [], {}
    for element in root.iter():
        if element.tag == "cite":
            route = re.fullmatch(r"\s*(\d{4})\s*年历史更新[（(]归档[）)]\s*", element.get("title", ""))
            if route:
                routes[int(route[1])] = daily.inline_content(element)[1][0]["url"]
        if re.fullmatch(r"h[1-6]", element.tag):
            label = daily.inline_content(element)[0].strip()
            month = re.fullmatch(r"(\d{4})\s*年\s*\d{1,2}\s*月", label)
            if month:
                year = int(month[1])
                batch = None
            day = re.fullmatch(r"(?:(\d{4})\s*年\s*)?(\d{1,2})\s*月\s*(\d{1,2})\s*日", label)
            if day:
                y = int(day[1]) if day[1] else year or current_day.year
                batch = date(y, int(day[2]), int(day[3]))
                if not day[1] and year is None and batch > current_day:
                    batch = date(y - 1, int(day[2]), int(day[3]))
        if element.tag not in {"li", "p"} or not batch or batch < daily.SUPPORTED_FROM:
            continue
        # 只处理本块的行内内容；容器中的子列表由遍历单独处理，避免重复。
        text, links = daily.inline_content(element)
        if not text.strip():
            continue
        references = [link for link in links if link["kind"] == "document_reference"]
        if len(references) != 1:
            unsupported.append({"date": str(batch), "block_id": element.get("id"), "reason": "非单篇文章引用"})
            continue
        ref = references[0]
        if ref["url"] == daily.HISTORY_URL and text.startswith("阅读更多："):
            continue
        prefix = "《" + ref["title"] + "》"
        if not text.lstrip().startswith(prefix):
            unsupported.append({"date": str(batch), "block_id": element.get("id"), "reason": "标题包裹格式未覆盖"})
            continue
        summary = text.lstrip()[len(prefix):]
        records.append({"article_id": ref["url"].rsplit("/", 1)[-1], "url": ref["url"],
                        "title": ref["title"], "date": str(batch), "summary": summary,
                        "log_url": source, "log_block_id": element.get("id")})
    return records, unsupported, routes


class Prototype:
    """本次运行的只读调用上下文：保存临时缓存、调用证据及五个工具的中间状态。"""

    def __init__(self, cache_dir, profile=None):
        """以 cache_dir 和可选 profile 初始化原型；返回实例，目录仅保存可清除实验数据。"""
        self.cache = Path(cache_dir).resolve()
        self.cache.mkdir(parents=True, exist_ok=True)
        self.run_dir = Path(tempfile.mkdtemp(prefix="zen43-run-"))
        self.profile = profile
        self.calls = []
        self.sources = []

    def call(self, arguments):
        """执行 arguments 中的只读 CLI，立即去评论；返回响应并在临时目录记录去评论后的证据。"""
        if arguments[:2] not in [["docs", "+fetch"], ["drive", "+search"], ["wiki", "+node-get"], ["docs", "+media-preview"]]:
            raise ValueError("原型只允许指定的四类只读 CLI 调用")
        args = [*arguments, "--as", "user", "--format", "json"]
        if self.profile:
            args += ["--profile", self.profile]
        started = time.monotonic()
        response = daily.run_cli(args)
        removed = strip_comments(response)
        path = write_json(self.run_dir / f"call-{len(self.calls) + 1:03}.json", response)
        document = response.get("data", {}).get("document", {})
        self.calls.append({"arguments": args, "seconds": round(time.monotonic() - started, 3),
                           "evidence_path": path, "revision": document.get("revision_id"),
                           "content_chars": len(document.get("content", "")), "comments_removed": removed})
        return response

    def fetch(self, article, scope="full", format="xml", **options):
        """按 article、scope、format 及 CLI 选项读取最新内容；返回 document，显式提示或节选不得当全文。"""
        max_depth = options.pop("max_depth", -1)
        args = ["docs", "+fetch", "--doc", article, "--scope", scope, "--doc-format", format,
                "--detail", "with-ids" if format == "xml" else "simple", "--max-depth", str(max_depth)]
        for name, value in options.items():
            args += ["--" + name.replace("_", "-"), str(value)]
        document = self.call(args)["data"]["document"]
        if document.get("tips"):
            raise ValueError("原生读取含 tips；需 ZEN-44 核对，不输出完整成功")
        if scope in {"full", "section", "range"} and "<excerpt" in document.get("content", ""):
            raise ValueError("原生读取仍为 excerpt，当前原型不能证明选区完整")
        return document

    def source(self, url, recent=False):
        """检查 url 的最新修订，未变则复用解析缓存；recent 指入口日志，返回来源记录与年份路由。"""
        check = self.fetch(url, "outline", max_depth=1)
        key = hashlib.sha256(((self.profile or "default") + url).encode()).hexdigest()[:20]
        path = self.cache / (key + ".json")
        cached = json.loads(path.read_text()) if path.exists() else None
        revision = check.get("revision_id")
        hit = bool(cached and cached.get("parser_version") == PARSER_VERSION
                   and revision is not None and cached["revision"] == revision)
        if not hit:
            if recent:
                headings = [h for h in xml_root(check["content"]).iter("h1") if daily.SECTION in daily.inline_content(h)[0]]
                if len(headings) != 1:
                    raise ValueError("无法唯一定位近期日志")
                document = self.fetch(url, "section", start_block_id=headings[0].get("id"))
            else:
                document = self.fetch(url)
            if revision != document.get("revision_id"):
                raise ValueError("日志在检查与读取间发生更新；不混用修订")
            records, unsupported, routes = log_entries(document["content"], url, datetime.now(daily.reading_timezone()).date())
            cached = {"parser_version": PARSER_VERSION, "revision": revision,
                      "records": records, "unsupported": unsupported, "routes": routes}
            write_json(path, cached)
        self.sources.append({"url": url, "revision": revision, "cache_hit": hit,
                             "records": len(cached["records"]), "unsupported": cached["unsupported"]})
        return cached

    def pool(self):
        """按需检查近期页及支持期年度归档；返回按文章保留最近记录的索引，空摘要最后排除。"""
        recent = self.source(daily.SOURCE_URL, recent=True)
        archive = self.source(daily.HISTORY_URL)
        records = recent["records"] + archive["records"]
        for year, url in archive["routes"].items():
            if int(year) >= daily.SUPPORTED_FROM.year:
                records += self.source(url)["records"]
        latest = {}
        for record in records:
            old = latest.get(record["article_id"])
            if old is None or record["date"] > old["date"]:
                latest[record["article_id"]] = record
        self.latest_records = latest
        self.log_records = records
        return {key: record for key, record in latest.items() if record["summary"].strip()}

    def resolve(self, article):
        """把 article URL/token 解析成固定社区的 Wiki 与文档标识；返回最小身份映射，失败不猜别名。"""
        data = self.call(["wiki", "+node-get", "--node-token", article, "--space-id", SPACE])["data"]
        return {key: data.get(key) for key in ("node_token", "obj_token", "obj_type", "space_id", "title")}

    def search(self, query=None, since=None, until=None, page_size=5, cursor=None):
        """执行知识库检索或续页；输入查询/日期/页大小/快照游标，返回日期倒序页及覆盖状态。"""
        if page_size < 1:
            raise ValueError("page_size 必须为正整数")
        if cursor:
            snapshot, offset = cursor.split(":")
            if not re.fullmatch(r"[a-f0-9]{24}", snapshot):
                raise ValueError("无效原型游标")
            saved = json.loads((self.cache / (snapshot + ".snapshot.json")).read_text())
            rows, start, coverage = saved["rows"], int(offset), saved["coverage"]
        else:
            if not query and not since and not until:
                raise ValueError("查询语句、日期范围至少一项")
            if query and len(query) > 30:
                raise ValueError("查询最多 30 个字符，不截短")
            for day in (since, until):
                if day and date.fromisoformat(day) < daily.SUPPORTED_FROM:
                    raise ValueError("日志支持起点为 2025-06-01")
            if since and until and since > until:
                raise ValueError("开始日期晚于结束日期")
            pool = self.pool()
            candidates, pages = {}, 0
            if query:
                token = None
                while True:
                    args = ["drive", "+search", "--query", query, "--space-ids", SPACE, "--page-size", "20"]
                    if token:
                        args += ["--page-token", token]
                    data = self.call(args)["data"]
                    pages += 1
                    if data.get("notice"):
                        raise ValueError("原生搜索含 notice，需核对")
                    for item in data.get("results", []):
                        candidates[item["result_meta"]["token"]] = item
                    if not data.get("has_more"):
                        break
                    token = data["page_token"]
                selected = {key: value for key, value in pool.items() if key in candidates}
            else:
                selected = pool
            rows = []
            for key, item in selected.items():
                if (since and item["date"] < since) or (until and item["date"] > until):
                    continue
                row = {field: item[field] for field in ("article_id", "url", "title", "date")}
                if query:
                    candidate = candidates[key]
                    # 评论定位片段不交付；此类候选须后续通过正文定位决定，不伪装可靠片段。
                    if "comment_id" in candidate["result_meta"].get("url", ""):
                        row["snippet_status"] = "comment_match_not_delivered"
                    else:
                        row["snippet"] = candidate.get("summary_highlighted", "")
                rows.append(row)
            rows.sort(key=lambda row: (row["date"], row["article_id"]), reverse=True)
            unknown = sorted(set(candidates) - set(pool)) if query else []
            coverage = {"sources": self.sources, "native_pages": pages, "native_candidates": len(candidates),
                        "eligible_pool": len(pool), "unmatched_candidate_count": len(unknown),
                        "unmatched_sample": unknown[:5], "server_recall_guaranteed": False,
                        "status": "sample_pipeline_only" if unknown or any(s["unsupported"] for s in self.sources) else "observed_sources"}
            snapshot = hashlib.sha256((str(time.time_ns()) + str(self.run_dir)).encode()).hexdigest()[:24]
            write_json(self.cache / (snapshot + ".snapshot.json"), {"rows": rows, "coverage": coverage,
                        "query": query, "since": since, "until": until})
            start = 0
        end = start + page_size
        return {"results": rows[start:end], "total_in_snapshot": len(rows),
                "next_cursor": f"{snapshot}:{end}" if end < len(rows) else None, "coverage": coverage}

    def summaries(self, articles):
        """批量读取 articles 对应的最近原摘要；返回按输入对应的结果及来源覆盖，不生成新摘要。"""
        pool = self.pool()
        results = []
        for article in articles:
            token = urlparse(article).path.rstrip("/").rsplit("/", 1)[-1] if "://" in article else article
            if token not in self.latest_records:
                token = self.resolve(article)["node_token"]
            record = pool.get(token)
            if record:
                results.append({"input": article, "status": "found", **record})
            else:
                results.append({"input": article, "status": "not_found_in_observed_logs", "article_id": token})
        return {"results": results, "sources": self.sources}

    def structure(self, article, section=None, depth=1):
        """获取 article 在 section 下 depth 层实际标题；返回可读取单位，depth=1 表示直接子层。"""
        if depth < 1:
            raise ValueError("展开深度须为正整数")
        document = self.fetch(article)
        _, units, _ = section_model(document["content"])
        base = next((u for u in units if u["id"] == section), None) if section else None
        if section and not base:
            raise ValueError("不是可选的顶层章节")
        visible = [u for u in units if (section in u["parents"] and u["depth"] <= base["depth"] + depth)] if base else [u for u in units if u["depth"] <= depth]
        return {"article": article, "revision": document["revision_id"], "units": visible}

    def locate(self, article, keywords):
        """在 article 中以 keywords 的 OR 查询定位；补齐章节链与 excerpt 容器，返回所有本次命中。"""
        full = self.fetch(article)
        blocks, units, positions = section_model(full["content"])
        hits = self.fetch(article, "keyword", keyword="|".join(keywords), context_before=0, context_after=0)
        if hits["revision_id"] != full["revision_id"]:
            raise ValueError("定位时文章发生更新")
        root = xml_root(hits["content"])
        output, seen = [], set()
        for element in top_blocks(root):
            container_id = element.get("top-block-id") if element.tag == "excerpt" else None
            block_id = container_id or element.get("id")
            if not block_id or block_id in seen:
                continue
            seen.add(block_id)
            content = ET.tostring(element, encoding="unicode")
            if container_id:
                complete = self.fetch(article, "range", start_block_id=container_id, end_block_id=container_id)
                if complete["revision_id"] != full["revision_id"]:
                    raise ValueError("补全容器时文章发生更新")
                content = complete["content"]
            index = positions.get(block_id)
            if index is None:
                raise ValueError("命中块无法映射到当前全文，不猜位置")
            chain = [u for u in units if u["start"] <= index < u["end"]]
            output.append({"block_id": block_id, "snippet_xml": content, "container_expanded": bool(container_id),
                           "section_chain": [{"id": u["id"], "title": u["title"]} for u in chain],
                           "read_unit": chain[-1]["id"] if chain else "@document"})
        return {"article": article, "revision": full["revision_id"], "keywords": keywords, "hits": output,
                "completeness": "本次原生返回集；不保证服务端任意大文档无上限"}

    def read(self, article, sections=None, start=None, end=None):
        """读取 article 全文/多章/完整章节范围；返回 Markdown 绝对路径、实际选区和本地图片信息。"""
        if sections and (start or end):
            raise ValueError("章节列表与范围不能同时指定")
        full = self.fetch(article)
        blocks, units, _ = section_model(full["content"])
        by_id = {unit["id"]: unit for unit in units}
        if sections:
            intervals = [(by_id[key]["start"], by_id[key]["end"]) for key in sections]
        elif start or end:
            intervals = [(by_id[start]["start"] if start else 0, by_id[end]["end"] if end else len(blocks))]
        else:
            intervals = [(0, len(blocks))]
        merged = []
        for left, right in sorted(intervals):
            if left >= right:
                raise ValueError("章节范围顺序不正确")
            if merged and left <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(right, merged[-1][1]))
            else:
                merged.append((left, right))
        markdown, images, ranges, warnings = [], {}, [], []
        # macOS 的默认临时目录不在 lark-cli 输出白名单；使用它明确支持的 /tmp。
        folder = Path(tempfile.mkdtemp(prefix="zen43-body-", dir="/tmp")).resolve()
        for left, right in merged:
            first, last = blocks[left].get("id"), blocks[right - 1].get("id")
            if not first or not last:
                raise ValueError("选区端点缺少块标识")
            if not sections and not start and not end:
                body = self.fetch(article, "full", format="markdown")
            else:
                body = self.fetch(article, "range", format="markdown", start_block_id=first, end_block_id=last)
            if body["revision_id"] != full["revision_id"]:
                raise ValueError("正文与章节结构修订不一致")
            content = body["content"]
            for block in blocks[left:right]:
                for image in block.iter("img"):
                    token = image.get("src")
                    if not token:
                        continue
                    if token not in images:
                        try:
                            result = self.call(["docs", "+media-preview", "--token", token, "--output", str(folder / token)])
                            images[token] = result["data"]
                        except ValueError as error:
                            images[token] = {"status": "failed", "reason": str(error)}
                            warnings.append("图片获取失败：" + token + "；" + str(error))
                    saved = images[token].get("saved_path")
                    if saved:
                        content = content.replace("https://feishu.cn/file/" + token, str(Path(saved).resolve()))
                    else:
                        content = content.replace("https://feishu.cn/file/" + token, "图片获取失败:" + token)
            markdown.append(content)
            ranges.append({"start_block_id": first, "end_block_id": last, "top_level_blocks": right - left,
                           "units": [u["id"] for u in units if left <= u["start"] < right]})
        path = folder / "body.md"
        path.write_text("\n\n".join(markdown), encoding="utf-8")
        return {"article": article, "revision": full["revision_id"], "markdown_path": str(path),
                "actual_ranges": ranges, "images": images, "warnings": warnings,
                "scope": "full" if not sections and not start and not end else "selected_sections"}


def main():
    """解析命令行五入口与参数，打印完整 JSON 状态；返回退出码，执行证据写入临时目录。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=["search", "summaries", "locate", "structure", "read"])
    parser.add_argument("--article", default=SAMPLE)
    parser.add_argument("--articles", nargs="+")
    parser.add_argument("--query")
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--page-size", type=int, default=5)
    parser.add_argument("--cursor")
    parser.add_argument("--keywords", nargs="+", default=["MarkItDown", "MinerU"])
    parser.add_argument("--section")
    parser.add_argument("--sections", nargs="+")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "zen43-PROTOTYPE-wipe-me"))
    parser.add_argument("--profile")
    args = parser.parse_args()
    prototype = Prototype(args.cache_dir, args.profile)
    try:
        if args.tool == "search":
            result = prototype.search(args.query, args.since, args.until, args.page_size, args.cursor)
        elif args.tool == "summaries":
            result = prototype.summaries(args.articles or [args.article])
        elif args.tool == "structure":
            result = prototype.structure(args.article, args.section, args.depth)
        elif args.tool == "locate":
            result = prototype.locate(args.article, args.keywords)
        else:
            result = prototype.read(args.article, args.sections, args.start, args.end)
        write_json(prototype.run_dir / "calls.json", prototype.calls)
        print(json.dumps({"result": result, "evidence_dir": str(prototype.run_dir)}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, OSError, ET.ParseError) as error:
        write_json(prototype.run_dir / "calls.json", prototype.calls)
        print(json.dumps({"status": "prototype_error", "error": str(error), "evidence_dir": str(prototype.run_dir)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
