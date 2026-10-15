"""通过官方 lark-cli 按更新日志日期取得 WaytoAGI 的原始更新条目。

--date 必填；自动定位近期页面或年度归档，支持从2025-06-01起的页面记录。
日期采用 Asia/Singapore；未找到批次、超出支持范围和读取失败分别表达。
CLI 负责用户身份和凭证续期；本脚本只解析其响应，不自行登录或匿名读取。
"""

import argparse
from datetime import date, datetime
import json
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from xml.etree import ElementTree


SOURCE_URL = "https://waytoagi.feishu.cn/wiki/QPe5w5g7UisbEkkow8XcDmOpn8e"
SOURCE_DOCUMENT_ID = "NDsAdX4spozsglxgqm7caJqdnVf"
HISTORY_URL = "https://waytoagi.feishu.cn/wiki/FjiOwWp2giA7hRk6jjfcPioCnAc"
SUPPORTED_FROM = date(2025, 6, 1)
SECTION = "近 7 日更新日志"
INLINE_TAGS = {"cite", "a", "b", "i", "u", "s", "strong", "em", "code", "span", "br"}


def reading_timezone():
    """无参数，返回来源使用的时区；缺数据时给出恢复提示，不替换为机器当地时区。

    延后到 main 的错误处理范围内加载，避免新机器缺时区数据时在导入阶段崩溃。
    """
    try:
        return ZoneInfo("Asia/Singapore")
    except ZoneInfoNotFoundError as error:
        raise ValueError("TIMEZONE_DATA_MISSING: 请在运行此脚本的 Python 环境补齐 tzdata，再重试") from error


def run_cli(arguments):
    """执行官方 CLI 的只读命令；输入参数列表，返回成功 JSON，失败抛 ValueError。

    stdout 为业务结果，stderr 可能是结构化错误或普通诊断。只保留错误码、
    消息及缺失权限，不回显任意诊断，也不启动授权或其他读取路线。
    """
    try:
        process = subprocess.run(
            ["lark-cli", *arguments], capture_output=True, text=True, timeout=90, check=False,
        )
    except FileNotFoundError as error:
        raise ValueError("CLI_NOT_FOUND: 请按 setup.md 准备官方 lark-cli，并确认当前执行环境可找到命令") from error
    except subprocess.TimeoutExpired as error:
        raise ValueError("CLI_TIMEOUT: 官方读取超过 90 秒；检查网络或服务状态后，按失败处理约定重试") from error
    response = None
    for output in (process.stdout, process.stderr):
        try:
            candidate = json.loads(output)
        except ValueError:
            # 自动续期可能先在 stderr 输出诊断，再输出业务错误 JSON。
            # 只提取完整结果对象，保留错误原因而不回显诊断或凭证信息。
            candidate = None
            for match in re.finditer(r"(?m)^[ \t]*\{", output):
                try:
                    parsed, _ = json.JSONDecoder().raw_decode(output[match.start():].lstrip())
                except ValueError:
                    continue
                if isinstance(parsed, dict) and "ok" in parsed:
                    candidate = parsed
                    break
        if isinstance(candidate, dict):
            response = candidate
            break
    if response is None:
        raise ValueError(f"CLI_FAILED: 未取得结构化响应（退出码 {process.returncode}）")
    if process.returncode or response.get("ok") is not True:
        error = response.get("error", {})
        if not isinstance(error, dict):
            error = {}
        reason = str(error.get("code", "CLI_FAILED")) + ": " + str(error.get("message", "官方 CLI 获取失败"))
        if error.get("missing_scopes"):
            reason += "; missing_scopes=" + json.dumps(error["missing_scopes"], ensure_ascii=False)
        raise ValueError(reason)
    if response.get("identity") != "user":
        raise ValueError("WRONG_IDENTITY: WaytoAGI 获取必须使用 --as user")
    return response


def inline_content(element):
    """还原 DocxXML 行内文字和链接；输入 XML 元素，返回 (原文字, 链接列表)。

    cite 的标题位于属性中，普通 itertext 会丢掉它。文档引用用 API 返回的
    类型和标识构造标准链接；已有 URL 则原样保留。块级子节点由外层单独处理。
    """
    if element.tag == "cite":
        title = element.get("title", "")
        token = element.get("doc-id", "")
        file_type = element.get("file-type", "")
        url = element.get("url") or element.get("href")
        if not title.strip():
            raise ValueError("INVALID_REFERENCE: 文档引用缺少标题")
        if not url:
            if file_type not in {"wiki", "docx"} or not re.fullmatch(r"[A-Za-z0-9]+", token):
                raise ValueError("INVALID_REFERENCE: 文档引用缺少可识别的类型或标识")
            url = f"https://waytoagi.feishu.cn/{file_type}/{token}"
        return title, [{"title": title, "url": url, "kind": "document_reference"}]
    if element.tag == "br":
        return "\n", []
    text = element.text or ""
    links = []
    for child in element:
        if child.tag in INLINE_TAGS:
            child_text, child_links = inline_content(child)
            text += child_text
            links.extend(child_links)
        elif element.tag in INLINE_TAGS:
            raise ValueError("ENTRY_FORMAT_CHANGED: 未支持的嵌套行内结构 " + child.tag)
        text += child.tail or ""
    if element.tag == "a":
        url = element.get("href") or element.get("url")
        if not url:
            raise ValueError("INVALID_REFERENCE: 超链接没有实际 URL")
        links.append({"title": text, "url": url, "kind": "url"})
    return text, links


def append_xml_blocks(element, blocks, depth=1, ordered=False):
    """将嵌套 XML 按原顺序展开为正文块；输入元素、结果列表和层级，无返回值。

    CLI 会把条目嵌在日期标题内部，不能把整棵标题子树当成日期文字。
    列表容器自身不算正文块；标题、条目、段落和图片各保留自己的 ID。
    """
    if element.tag in {"ul", "ol"}:
        if (element.text or "").strip() or any((child.tail or "").strip() for child in element):
            raise ValueError("ENTRY_FORMAT_CHANGED: 列表容器中出现无法归属条目的文字")
        for child in element:
            append_xml_blocks(child, blocks, depth, element.tag == "ol")
        return
    if re.fullmatch(r"h[1-6]", element.tag):
        block_type = "heading" + element.tag[1:]
    elif element.tag in {"p", "li", "img", "hr"}:
        block_type = {"p": "text", "li": "ordered" if ordered else "bullet", "img": "image", "hr": "divider"}[element.tag]
    else:
        raise ValueError("ENTRY_FORMAT_CHANGED: 未支持的 CLI 正文结构 " + element.tag)
    block_id = element.get("id")
    if not block_id:
        raise ValueError("BLOCK_ID_MISSING: CLI 正文缺少块 ID，请使用 --detail full")
    text, links = inline_content(element)
    blocks.append({"id": block_id, "type": block_type, "depth": depth, "text": text, "links": links})
    for child in element:
        if child.tag not in INLINE_TAGS:
            append_xml_blocks(child, blocks, depth + 1)


def document_from_cli(response, fetched_at, source_url=SOURCE_URL, document_id=SOURCE_DOCUMENT_ID):
    """将章节响应转成正文块；输入响应、抓取时间、来源及预期文档标识，返回 dict。

    只接受已定位来源的用户身份响应、完整 section XML 和可识别正文结构。
    节选、截断或读取提示需要另行核对，不能据此宣称批次完整。
    """
    if response.get("ok") is not True or response.get("identity") != "user":
        raise ValueError("CLI_FAILED: 需要成功的用户身份 CLI 响应")
    document = response["data"]["document"]
    if not isinstance(document, dict) or not isinstance(document.get("content"), str):
        raise ValueError("INVALID_RESPONSE: CLI 未返回可解析的文档正文")
    if document.get("document_id") != document_id:
        raise ValueError("WRONG_SOURCE: CLI 响应不是已定位的 WaytoAGI 更新文档")
    try:
        fragment = ElementTree.fromstring(document["content"])
    except ElementTree.ParseError as error:
        raise ValueError("INCOMPLETE_SOURCE: CLI 正文 XML 无法完整解析") from error
    if fragment.tag != "fragment" or fragment.get("mode") != "section":
        raise ValueError("WRONG_SECTION: 必须使用 CLI section 读取更新日志")
    if fragment.find(".//excerpt") is not None or document.get("tips"):
        raise ValueError("INCOMPLETE_SOURCE: CLI 返回节选或读取提示，需要核对缺失范围")
    blocks = []
    for element in fragment:
        append_xml_blocks(element, blocks)
    if not blocks or blocks[0]["id"] != fragment.get("requested-start"):
        raise ValueError("WRONG_SECTION: CLI 结果没有从请求的板块标题开始")
    return {
        "status": "ok", "source_url": source_url, "fetched_at": fetched_at,
        "scope_complete": True, "blocks": blocks, "access_method": "lark-cli",
        "document_id": document["document_id"], "revision_id": document.get("revision_id"),
    }


def fetch_cli_section(profile=None):
    """通过官方 CLI 定位并读取更新板块；参数 profile 为命名配置名或 None，返回经过校验的正文块对象。

    每次从一级目录定位当前块 ID，避免把会变化的板块位置硬编码。
    两次读取都显式使用用户身份；指定 profile 时两次调用都携带同一 --profile，
    保证独立命名配置的验收不落到默认配置上。认证、网络或结构错误直接交给调用方处理。
    """
    common = ["docs", "+fetch", "--doc", SOURCE_URL, "--as", "user", "--doc-format", "xml", "--format", "json"]
    if profile:
        common += ["--profile", profile]
    outline = run_cli([*common, "--scope", "outline", "--max-depth", "1", "--detail", "with-ids"])
    try:
        tree = ElementTree.fromstring(outline["data"]["document"]["content"])
    except ElementTree.ParseError as error:
        raise ValueError("INVALID_OUTLINE: CLI 目录无法完整解析") from error
    headings = [heading for heading in tree.iter("h1") if SECTION in "".join(heading.itertext())]
    if len(headings) != 1 or not headings[0].get("id"):
        raise ValueError("SECTION_NOT_FOUND: CLI 目录无法唯一定位近 7 日更新日志")
    response = run_cli([*common, "--scope", "section", "--start-block-id", headings[0].get("id"), "--detail", "full"])
    return document_from_cli(response, datetime.now(reading_timezone()).isoformat())


def read_archive_page(source_url, profile, scope="outline", start_block_id=None):
    """读取归档目录或章节；输入来源、配置、范围及锚点，返回原响应与已校验 XML。

    只调用 CLI 的用户身份读取；CLI 故障由调用方报告，不在这里登录或重试。
    """
    arguments = ["docs", "+fetch", "--doc", source_url, "--as", "user",
                 "--scope", scope, "--detail", "full" if scope == "section" else "with-ids",
                 "--doc-format", "xml", "--format", "json"]
    if start_block_id:
        arguments += ["--start-block-id", start_block_id]
    if profile:
        arguments += ["--profile", profile]
    response = run_cli(arguments)
    data = response.get("data")
    document = data.get("document") if isinstance(data, dict) else None
    if not isinstance(document, dict) or not document.get("document_id"):
        raise ValueError("INVALID_RESPONSE: 归档没有返回文档标识")
    try:
        root = ElementTree.fromstring(document["content"])
    except (KeyError, TypeError, ElementTree.ParseError) as error:
        raise ValueError("INCOMPLETE_SOURCE: 归档 XML 无法完整解析") from error
    if root.tag != "fragment" or root.get("mode") != scope:
        raise ValueError("WRONG_SECTION: 归档响应范围与请求不符")
    if document.get("tips") or root.find(".//excerpt") is not None:
        raise ValueError("INCOMPLETE_SOURCE: 归档存在节选或限制提示")
    if start_block_id and root.get("requested-start") != start_block_id:
        raise ValueError("WRONG_SECTION: 归档没有从请求的标题开始")
    return response, root


def archive_date_index(root, year=None):
    """从归档目录建立日期索引；输入 XML 与已确认年份，返回（日期，锚点）列表。

    年份来自目录的年月标题或年份路由，不能用用户请求的日期为来源补年份。
    """
    dates = []
    for heading in root.iter():
        if not re.fullmatch(r"h[1-6]", heading.tag):
            continue
        text = heading.text or ""
        month = re.match(r"\s*(\d{4})\s*年\s*\d{1,2}\s*月", text)
        if month:
            year = int(month.group(1))
            continue
        day = re.match(r"\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
        if day and year:
            dates.append((date(year, *map(int, day.groups())), heading.get("id")))
    if not dates or any(not anchor for _, anchor in dates):
        raise ValueError("DATE_HEADINGS_MISSING: 归档目录没有可定位的日期")
    return dates


def fetch_archive_date(target_date, profile, fetched_at):
    """按日期沿年度路由读取批次；输入日期、配置及抓取时间，返回统一结果字典。"""
    source_url = HISTORY_URL
    searched_sources = [SOURCE_URL, HISTORY_URL]
    response, root = read_archive_page(source_url, profile)
    dates = archive_date_index(root)
    if target_date.year not in {day.year for day, _ in dates}:
        notices = [h for h in root.iter() if re.fullmatch(r"h[1-6]", h.tag) and (h.text or "").strip() == "温馨提示"]
        if len(notices) != 1 or not notices[0].get("id"):
            raise ValueError("ARCHIVE_ROUTES_MISSING: 无法定位归档年份说明")
        intro_response, intro = read_archive_page(source_url, profile, "section", notices[0].get("id"))
        if intro_response["data"]["document"]["document_id"] != response["data"]["document"]["document_id"]:
            raise ValueError("WRONG_SOURCE: 年份路由与已定位的归档文档不符")
        routes = {}
        for reference in intro.iter("cite"):
            match = re.fullmatch(r"\s*(\d{4})\s*年历史更新[（(]归档[）)]\s*", reference.get("title", ""))
            if match:
                _, links = inline_content(reference)
                year = int(match.group(1))
                if year in routes:
                    raise ValueError("AMBIGUOUS_ARCHIVE: 同一年存在多个归档入口")
                routes[year] = links[0]["url"]
        if target_date.year not in routes:
            raise ValueError("ARCHIVE_YEAR_MISSING: 当前归档缺少目标年份入口，需要核对来源")
        source_url = routes[target_date.year]
        searched_sources.append(source_url)
        response, root = read_archive_page(source_url, profile)
        dates = archive_date_index(root, target_date.year)
    matches = [anchor for day, anchor in dates if day == target_date]
    if len(matches) > 1:
        raise ValueError("AMBIGUOUS_DATE: 归档中同一日期有多个标题，不能任取一个")
    result = {"status": "date_batch_not_present", "source_url": source_url,
              "fetched_at": fetched_at, "timezone": "Asia/Singapore",
              "target_date": target_date.isoformat(), "entries": [],
              "available_dates": [day.isoformat() for day, _ in dates if day >= SUPPORTED_FROM],
              "searched_sources": searched_sources,
              "message": "已检查更新页面，未找到目标日期批次；不等于当天没有更新"}
    if not matches:
        return result
    section, _ = read_archive_page(source_url, profile, "section", matches[0])
    document = document_from_cli(section, fetched_at, source_url, response["data"]["document"]["document_id"])
    heading = document["blocks"][0]
    expected = re.fullmatch(r"\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*", heading["text"])
    if heading["type"] != "heading3" or not expected or tuple(map(int, expected.groups())) != (target_date.month, target_date.day):
        raise ValueError("WRONG_SECTION: 返回的章节日期与目录定位不符")
    entries, skipped_images = extract_entries(document["blocks"][1:])
    result.update(status="ok", entries=entries, skipped_image_blocks=skipped_images,
                  scope_complete=True, document_id=document["document_id"],
                  revision_id=document.get("revision_id"))
    result.pop("message")
    return result


def extract_entries(blocks):
    """提取一个日期下的文章；输入有序正文块，返回（原始条目列表，跳过图片数）。

    当前支持范围使用《标题》加摘要的格式。缺标题、缺真实链接或未知结构时
    明确失败，避免兼容早期杂项记录而把不完整材料当作成功。
    """
    entries = []
    skipped_images = 0
    for block in blocks:
        if block["type"] == "image":
            skipped_images += 1
            continue
        if not block["text"].strip():
            continue
        if block["type"] not in {"bullet", "ordered", "text"}:
            raise ValueError("ENTRY_FORMAT_CHANGED: 出现未支持的非空文字块，需要检查原页")
        match = re.fullmatch(r"\s*《\s*(.*?)\s*》(.*)", block["text"], re.DOTALL)
        links = block.get("links", [])
        if not match or not match.group(1).strip() or not links:
            raise ValueError("ENTRY_FORMAT_CHANGED: 条目缺少可验证的标题或真实链接；请核对 CLI 正文")
        entries.append({"title": match.group(1).strip(), "summary": match.group(2),
                        "links": links, "source_block_id": block["id"]})
    if not entries:
        raise ValueError("EMPTY_BATCH: 目标日期标题存在，但没有取得条目；不能解释为无更新")
    return entries, skipped_images


def extract_daily(document, target_date):
    """从完整的更新板块提取目标日期，返回条目和日期覆盖信息。

    参数 document 是 CLI 响应转换后的完整近期板块，target_date 是必填 date。
    返回包含实际日期、原始条目和覆盖状态的 dict。
    年份缺失的标题按抓取当地日期推定最近一次该月日；结构异常抛 ValueError。
    """
    if document.get("status") != "ok" or not document.get("scope_complete"):
        raise ValueError("INCOMPLETE_SOURCE: 飞书更新板块没有通过完整性检查")
    if document.get("source_url", "").split("?")[0] != SOURCE_URL:
        raise ValueError("WRONG_SOURCE: 输入不是 WaytoAGI 入口")
    blocks = document["blocks"]
    if not blocks or blocks[0]["type"] != "heading1" or SECTION not in blocks[0]["text"]:
        raise ValueError("WRONG_SECTION: 输入必须是独立的近 7 日更新日志板块")
    if any(block["type"] in {"page", "heading1"} for block in blocks[1:]):
        raise ValueError("WRONG_SECTION: 输入混入了目标板块之外的内容")
    fetched_at = datetime.fromisoformat(document["fetched_at"].replace("Z", "+00:00"))
    if fetched_at.tzinfo is None:
        raise ValueError("INVALID_TIMESTAMP: 抓取时间缺少时区")
    fetched_date = fetched_at.astimezone(reading_timezone()).date()
    if target_date > fetched_date:
        raise ValueError("FUTURE_DATE: 目标日期晚于本次抓取日期")
    batches = []
    for block in blocks[1:]:
        if not block["type"].startswith("heading"):
            continue
        match = re.fullmatch(r"\s*(?:(\d{4})\s*年\s*)?(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*", block["text"])
        if not match:
            if block["text"].strip():
                raise ValueError("DATE_STRUCTURE_CHANGED: 出现非日期子标题，需要检查原页")
            continue
        if block["type"] != "heading3" or block["depth"] != blocks[0]["depth"]:
            raise ValueError("DATE_STRUCTURE_CHANGED: 日期批次的标题层级或位置变化")
        year, month, day = match.groups()
        # 闰日从最近的有效年份开始找；不能用目标日期反推年份，否则会把旧请求错配到今年。
        candidate = None
        for possible_year in ([int(year)] if year else range(fetched_date.year, fetched_date.year - 5, -1)):
            try:
                value = date(possible_year, int(month), int(day))
            except ValueError:
                continue
            if value <= fetched_date:
                candidate = value
                break
        if candidate is None:
            raise ValueError("INVALID_BATCH_DATE: 更新标题日期无效或晚于抓取日期")
        if batches and candidate >= batches[-1][0]:
            raise ValueError("INVALID_DATE_ORDER: 更新日期重复或顺序变化，需要检查原页")
        batches.append((candidate, block, year is None))
    if not batches:
        raise ValueError("DATE_HEADINGS_MISSING: 板块内没有可识别的日期标题")
    result = {
        "status": "ok", "source_url": SOURCE_URL,
        "fetched_at": document["fetched_at"], "timezone": "Asia/Singapore",
        "target_date": target_date.isoformat(), "latest_available_date": batches[0][0].isoformat(),
        "available_dates": [batch[0].isoformat() for batch in batches],
        "year_inference": "无年份标题取不晚于抓取当地日期的最近一次该月日",
        "scope_complete": True, "entries": [],
        "access_method": "lark-cli", "document_id": document.get("document_id"),
        "revision_id": document.get("revision_id"),
    }
    batch = next((batch for batch in batches if batch[0] == target_date), None)
    if batch is None:
        result["status"] = "outside_available_window" if target_date < batches[-1][0] else "date_batch_not_present"
        result["message"] = "目标日期不在当前展示窗口内" if result["status"] == "outside_available_window" else "完整更新板块中尚未出现目标日期批次；不等于已确认当天没有更新"
        return result
    heading = batch[1]
    start = blocks.index(heading) + 1
    heading_rank = int(heading["type"].removeprefix("heading"))
    selected_blocks = []
    for block in blocks[start:]:
        if block["type"].startswith("heading") and int(block["type"].removeprefix("heading")) <= heading_rank:
            break
        selected_blocks.append(block)
    result["entries"], result["skipped_image_blocks"] = extract_entries(selected_blocks)
    return result


def parse_date(value):
    """校验命令行日期；输入 YYYY-MM-DD 字符串，返回 date，无效时给出用法错误。"""
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("日期格式不符")
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("日期必须是有效的 YYYY-MM-DD") from error


def main():
    """执行官方 CLI 并打印单日 JSON；返回 0 表示已可靠观察，2 表示失败。

    --date 为必填更新日志日期；--input 用于离线复核附有抓取时间的近期章节 JSON。
    --profile 指定官方 CLI 命名配置，仅在线读取时传递，离线 --input 复核不使用。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=parse_date, required=True, help="更新日志日期，格式 YYYY-MM-DD")
    parser.add_argument("--input", type=Path, help="离线复核 section CLI JSON，须附加 fetched_at（含时区）")
    parser.add_argument("--profile", help="官方 CLI 命名配置名；省略时使用默认配置")
    args = parser.parse_args()
    try:
        if args.date > datetime.now(reading_timezone()).date():
            raise ValueError("FUTURE_DATE: 目标日期晚于当前来源时区日期")
        if args.date < SUPPORTED_FROM:
            print(json.dumps({"status": "outside_supported_range", "supported_from": SUPPORTED_FROM.isoformat(),
                              "target_date": args.date.isoformat(), "entries": [],
                              "message": "仅支持从2025-06-01起的更新日志日期"}, ensure_ascii=False))
            return 0
        if args.input:
            response = json.loads(args.input.read_text())
            document = document_from_cli(response, response["fetched_at"])
        else:
            document = fetch_cli_section(args.profile)
        result = extract_daily(document, args.date)
        if not args.input and result["status"] != "ok":
            result = fetch_archive_date(args.date, args.profile, document["fetched_at"])
        result["supported_from"] = SUPPORTED_FROM.isoformat()
        result.setdefault("searched_sources", [SOURCE_URL])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "error", "source_url": SOURCE_URL, "target_date": args.date.isoformat() if args.date else None, "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
