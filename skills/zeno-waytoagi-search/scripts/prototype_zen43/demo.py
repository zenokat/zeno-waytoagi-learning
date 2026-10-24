"""运行 ZEN-43 真实只读演示与针对性核对，生成可双击的自包含 HTML 结果页。

一个命令运行五工具主要路径。所有断言只核对本次实际样本，不替代 ZEN-44。
结果正文和原生证据留在临时目录；仓库只保存可重放代码及精简事实账本。
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import tempfile

from prototype import Prototype, SAMPLE, section_model, write_json, xml_root


def assert_images(result):
    """核对 result 的图片已落盘并嵌入 Markdown；返回本次图片数，任一失败抛断言异常。"""
    content = Path(result["markdown_path"]).read_text()
    assert not result["warnings"], result["warnings"]
    for item in result["images"].values():
        path = Path(item["saved_path"]).resolve()
        assert path.is_file() and path.stat().st_size > 0
        assert str(path) in content
    assert "https://feishu.cn/file/" not in content
    return len(result["images"])


def compact_result(result):
    """缩短用于便携 HTML 展示的 result，保留结构和计数；返回副本，完整结果仍存于本地证据。"""
    result = json.loads(json.dumps(result))
    if "hits" in result:
        result["hit_count"] = len(result["hits"])
        result["expanded_containers"] = sum(h["container_expanded"] for h in result["hits"])
        for hit in result["hits"]:
            hit.pop("snippet_xml", None)
    if "results" in result:
        for row in result["results"]:
            if "summary" in row:
                row["summary_chars"] = len(row.pop("summary"))
            row.pop("snippet", None)
    return result


def build_html(path, scenarios, checks):
    """把 scenarios 真实输入输出和 checks 核对结果嵌入单文件 HTML；返回文件绝对路径。"""
    payload = json.dumps({"scenarios": scenarios, "checks": checks}, ensure_ascii=False).replace("<", "\\u003c")
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>五个工具的真实调用演示</title><style>
body{font:16px/1.65 system-ui,sans-serif;color:#22313b;background:#f5f7f8;max-width:1080px;margin:48px auto;padding:0 24px}h1{font-size:30px}button{font:inherit;padding:10px 18px;border:1px solid #b9ccd2;border-radius:8px;background:white;cursor:pointer;margin:4px}button.active{background:#215b6c;color:white}section{background:white;padding:24px;border-radius:14px;margin:18px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 ui-monospace,monospace;background:#f2f5f6;padding:16px;border-radius:8px;max-height:520px;overflow:auto}.muted{color:#61717b}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.badge{display:inline-block;background:#e7f2ec;padding:4px 12px;border-radius:5px}@media(max-width:700px){.grid{grid-template-columns:1fr}}
</style><body><h1>五个工具的真实调用演示</h1>
<p>验证问题：已确认的五个统一工具，能否由 lark-cli 与最小封装实现？</p>
<p class="muted">可丢弃原型 · 这是一次真实只读运行的回放，切换按钮不会重新联网。点击各入口查看输入、转换结果和内部动作。完整正文与原生响应保存在本机临时目录；重新运行 demo.py 可重新验证。样本通过不代表全库完整保证。</p>
<section><span class="badge" id="status"></span><p id="checks"></p><button onclick="show(0)">从头演示</button><button onclick="next()">按旅程看下一步</button><div id="tabs"></div></section>
<section><h2 id="name"></h2><p id="explain"></p><div class="grid"><div><h3>输入</h3><pre id="input"></pre><details><summary>真实内部动作与调用参数</summary><pre id="native"></pre></details></div><div><h3>本次取得的结果</h3><div id="readable"></div><details><summary>查看全部结构化字段</summary><pre id="output"></pre></details></div></div></section>
<p class="muted">读取路径只表示文件已保存。图片路径只表示图片已获取，不能冒充 Agent 已看见图片。异常取舍交给后续原型阶段。</p>
<script>const evidence=PAYLOAD;let current=0;
/** 展示索引 index 对应的真实场景；输入数字索引，无返回值，刷新全部状态。 */
function show(index){current=index;const item=evidence.scenarios[index];document.getElementById('name').textContent=item.name;document.getElementById('explain').textContent=item.explain;document.getElementById('input').textContent=JSON.stringify(item.input,null,2);document.getElementById('native').textContent=JSON.stringify(item.native,null,2);document.getElementById('output').textContent=JSON.stringify(item.output,null,2);renderResult(item.output);document.getElementById('status').textContent='步骤 '+(index+1)+' / '+evidence.scenarios.length;document.querySelectorAll('#tabs button').forEach((b,i)=>b.classList.toggle('active',i===index));}
/** 将 result 的关键状态转为可读字段和列表；无返回值，完整字段仍可展开核对。 */
function renderResult(result){const panel=document.getElementById('readable');panel.replaceChildren();const lines=[];if(result.results){lines.push('本页 '+result.results.length+' 条'+(result.total_in_snapshot!==undefined?'；快照共 '+result.total_in_snapshot+' 条':''));result.results.forEach(r=>lines.push((r.date||'')+' '+(r.title||r.input)+(r.summary_chars!==undefined?'；原摘要 '+r.summary_chars+' 字符':'')));if(result.next_cursor)lines.push('可继续获取下一页');}if(result.coverage){lines.push('原生候选 '+result.coverage.native_candidates+' 个；已读取 '+result.coverage.native_pages+' 页');lines.push('未关联候选 '+result.coverage.unmatched_candidate_count+' 个，未当作没有摘要');}if(result.units){result.units.forEach(u=>lines.push('　'.repeat(u.depth-1)+u.title+'（第 '+u.depth+' 层）'));}if(result.hits){lines.push('命中 '+result.hit_count+' 个顶层单位；补全 '+result.expanded_containers+' 个容器');result.hits.forEach(h=>lines.push(h.section_chain.map(s=>s.title).join(' → ')+(h.container_expanded?'；容器已补全':'')));}if(result.markdown_path){lines.push('正文范围：'+(result.scope==='full'?'全文':'所选完整章节'));lines.push('合并后 '+result.actual_ranges.length+' 段；文内图片 '+Object.keys(result.images).length+' 张');lines.push('Markdown：'+result.markdown_path);lines.push(result.warnings.length?'素材存在未完成项':'本次素材均已获取');}lines.forEach(text=>{const p=document.createElement('p');p.textContent=text;panel.append(p);});}
/** 进入下一个真实场景；无参数、无返回值，末尾回到第一步。 */
function next(){show((current+1)%evidence.scenarios.length);}
/** 为场景 item 与索引 index 创建导航；返回按钮元素，不解释外部文本为 HTML。 */
function button(item,index){const b=document.createElement('button');b.textContent=item.name;b.onclick=()=>show(index);return b;}
evidence.scenarios.forEach((item,index)=>document.getElementById('tabs').append(button(item,index)));document.getElementById('checks').textContent=Object.entries(evidence.checks).map(([k,v])=>k+'：'+v).join('；');show(0);
</script></body></html>'''.replace("PAYLOAD", payload)
    Path(path).write_text(page, encoding="utf-8")
    return str(Path(path).resolve())


def run_demo(output):
    """在 output 目录执行真实五入口和正常语义核对；返回 HTML、证据路径和核对结论。"""
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    cache = output / "PROTOTYPE-wipe-me-cache"
    scenarios, checks = [], {}

    def capture(name, explanation, arguments, method, **kwargs):
        """用独立原型上下文执行 method；输入说明、显示参数和函数参数，返回结果与上下文。"""
        p = Prototype(cache)
        result = getattr(p, method)(**kwargs)
        write_json(p.run_dir / "calls.json", p.calls)
        result_path = write_json(p.run_dir / "result.json", result)
        native = []
        for call in p.calls:
            argv = list(call["arguments"])
            if "--page-token" in argv:
                argv[argv.index("--page-token") + 1] = "<原生续页令牌，仅本地保留>"
            native.append({"command": argv, "revision": call["revision"], "seconds": call["seconds"],
                           "content_chars": call["content_chars"]})
        scenarios.append({"name": name, "explain": explanation, "input": arguments,
                          "output": compact_result(result), "native": native, "local_result": result_path})
        print(name + "完成", flush=True)
        return result, p

    search, first = capture("知识库检索", "先读完原生候选，再关联社区日期并生成排序快照。未关联候选保留不确定状态。",
        {"query": "RAG", "page_size": 3}, "search", query="RAG", page_size=3)
    assert search["coverage"]["native_pages"] > 1
    second, _ = capture("检索下一页", "这里使用封装生成的结果快照游标；不会拿原生第二页冒充社区日期第二页。",
        {"cursor": "上一页返回的游标", "page_size": 3}, "search", cursor=search["next_cursor"], page_size=3)
    assert not set(x["article_id"] for x in search["results"]) & set(x["article_id"] for x in second["results"])
    dates = [x["date"] for x in search["results"] + second["results"]]
    assert dates == sorted(dates, reverse=True)
    checks["原生翻页"] = str(search["coverage"]["native_pages"]) + " 页已读至结束"
    checks["快照分页"] = "前两页无重复、日期倒序"

    dates_only, cached = capture("按日期发现", "先保留各文章最近一次记录，再筛日期；检查来源修订后复用缓存。摘要不随列表返回。",
        {"since": "2026-09-01", "until": "2026-09-30"}, "search", since="2026-09-01", until="2026-09-30")
    assert all(source["cache_hit"] for source in dates_only["coverage"]["sources"])
    assert all("summary" not in item for item in dates_only["results"])
    repeated = [r for r in cached.log_records if r["article_id"] == "YTt3wPPIeixEK5kbJPnc0YL7nTf"]
    assert len(repeated) > 1
    latest = max(repeated, key=lambda row: row["date"])
    assert cached.latest_records[latest["article_id"]] == latest
    checks["缓存"] = "三个来源修订不变，复用解析结果"
    checks["重复更新"] = f"{len(repeated)} 次记录归并为 {latest['date']} 及该次原摘要"

    summary, _ = capture("摘要读取", "批量返回社区原文摘要。演示页仅展示字数与来源，完整摘要见本地 result.json。",
        {"articles": [search["results"][0]["article_id"], latest["article_id"]]}, "summaries",
        articles=[search["results"][0]["article_id"], latest["article_id"]])
    assert all(r["status"] == "found" for r in summary["results"])
    assert summary["results"][1]["summary"] == latest["summary"]
    checks["批量摘要"] = "两篇均与原日志逐字一致"

    structure, _ = capture("篇章结构获取", "原文 H1 下直接接 H3；工具按真实父子关系返回第二层，而非用 H 数字当展开深度。",
        {"article": SAMPLE, "depth": 2}, "structure", article=SAMPLE, depth=2)
    children = [u for u in structure["units"] if u.get("rank") == 3 and u["depth"] == 2]
    assert children and all(len(u["parents"]) == 1 for u in children)
    checks["章节层级"] = "H1 → H3 识别为父子两层"

    located, _ = capture("全文检索", "OR 命中附完整章节链；表格 excerpt 会补为整表。此页不内嵌文章全文。",
        {"article": SAMPLE, "keywords": ["MarkItDown", "MinerU"]}, "locate", article=SAMPLE, keywords=["MarkItDown", "MinerU"])
    assert all(h["section_chain"] for h in located["hits"])
    assert any(h["container_expanded"] for h in located["hits"])
    for h in located["hits"]:
        if h["container_expanded"]:
            assert "<excerpt" not in h["snippet_xml"] and "MarkItDown" in h["snippet_xml"] and "MinerU" in h["snippet_xml"]
    # 单分支与 OR 的顶层命中集合比较，避免把嵌套节点数量说成独立命中数量。
    single_a = Prototype(cache).locate(SAMPLE, ["MarkItDown"])
    single_b = Prototype(cache).locate(SAMPLE, ["MinerU"])
    assert {h["block_id"] for h in located["hits"]} == {h["block_id"] for h in single_a["hits"] + single_b["hits"]}
    checks["OR 与容器"] = f"{len(located['hits'])} 个顶层命中单位；并集相等，表格补全"

    parent = next(u for u in structure["units"] if u["id"] == children[0]["parents"][0])
    body, _ = capture("正文读取", "选择父章和其中子章，重叠只输出一次；只获取选区里的图片并嵌入本地路径。",
        {"article": SAMPLE, "sections": [parent["id"], children[0]["id"]]}, "read",
        article=SAMPLE, sections=[parent["id"], children[0]["id"]])
    assert len(body["actual_ranges"]) == 1
    assert body["actual_ranges"][0]["top_level_blocks"] == parent["end"] - parent["start"]
    checks["多章合并与图片"] = f"重叠合并为一段，{assert_images(body)} 张图片已落盘并嵌入"

    bounded, _ = capture("完整章节范围", "终点虽然是章节标题，内部端点扩到该章末尾；不是读到终点标题就停止。",
        {"article": SAMPLE, "start": children[0]["id"], "end": children[1]["id"]}, "read",
        article=SAMPLE, start=children[0]["id"], end=children[1]["id"])
    assert bounded["actual_ranges"][0]["top_level_blocks"] == children[1]["end"] - children[0]["start"]
    assert bounded["actual_ranges"][0]["end_block_id"] != children[1]["id"]
    assert_images(bounded)
    checks["范围终点"] = "包括终章正文和子章节"

    complete, _ = capture("全文读取", "无章节参数读取全部正文，并自动获取文内图片；得到文件不代表 Agent 已读完。",
        {"article": SAMPLE}, "read", article=SAMPLE)
    checks["全文与图片"] = f"{complete['actual_ranges'][0]['top_level_blocks']} 个顶层块，{assert_images(complete)} 张图片"
    checks["验证时间"] = datetime.now().astimezone().isoformat(timespec="seconds")
    manifest = {"checks": checks, "scenarios": scenarios}
    write_json(output / "evidence.json", manifest)
    page = build_html(output / "demo.html", scenarios, checks)
    return {"html": page, "evidence": str(output / "evidence.json"), "checks": checks}


def main():
    """接收可选输出目录并运行演示；输出最终文件路径，失败保留已有临时证据。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=tempfile.mkdtemp(prefix="zen43-demo-", dir="/tmp"))
    args = parser.parse_args()
    print(json.dumps(run_demo(args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
