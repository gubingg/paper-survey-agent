from __future__ import annotations

import html
import re

import requests
import streamlit as st

st.set_page_config(page_title="多论文分析与研究空白验证平台", layout="wide")

TARGET_TYPE_LABELS = {
    "组会汇报": "meeting_outline",
    "论文综述": "survey",
    "研究空白分析": "gap_analysis",
}

EXPORT_TYPE_LABELS = {
    "论文综述": "survey",
    "组会汇报": "meeting_outline",
    "研究空白分析": "gap_analysis",
    "对比表": "compare_table",
}

FIELD_LABELS = {
    "datasets": "数据集",
    "metrics": "评测指标",
    "limitations": "局限性",
    "future_work": "未来工作",
}


@st.cache_data(show_spinner=False)
def app_style() -> str:
    return """
    <style>
    :root {
        --bg: linear-gradient(135deg, #f7f1e7 0%, #edf3fb 52%, #f8fbff 100%);
        --panel: rgba(255, 255, 255, 0.82);
        --stroke: rgba(23, 50, 77, 0.10);
        --ink: #18324c;
        --muted: #607287;
    }
    .stApp {
        background: var(--bg);
    }
    .block-container {
        max-width: 1260px;
        padding-top: 1.6rem;
        padding-bottom: 3rem;
    }
    .hero {
        padding: 2rem 2.2rem;
        border-radius: 28px;
        background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(255,247,241,0.92));
        border: 1px solid var(--stroke);
        box-shadow: 0 20px 48px rgba(27, 44, 67, 0.08);
        margin-bottom: 1rem;
    }
    .hero h1 {
        color: var(--ink);
        font-size: 2.15rem;
        margin-bottom: 0.35rem;
        letter-spacing: 0.02em;
    }
    .hero p {
        color: var(--muted);
        line-height: 1.8;
        margin: 0;
    }
    .metric-card {
        padding: 1rem 1.15rem;
        background: var(--panel);
        border-radius: 22px;
        border: 1px solid var(--stroke);
        box-shadow: 0 10px 30px rgba(33, 49, 72, 0.06);
        min-height: 108px;
    }
    .metric-card .label {
        color: var(--muted);
        font-size: 0.92rem;
    }
    .metric-card .value {
        margin-top: 0.35rem;
        color: var(--ink);
        font-size: 1.45rem;
        font-weight: 700;
        word-break: break-word;
    }
    .section-card {
        background: rgba(255,255,255,0.88);
        border-radius: 24px;
        padding: 1rem 1.2rem;
        border: 1px solid var(--stroke);
        box-shadow: 0 10px 28px rgba(35, 48, 69, 0.05);
        margin-bottom: 1rem;
    }
    .section-card h3 {
        color: var(--ink);
        margin: 0 0 0.45rem 0;
        font-size: 1.08rem;
    }
    .section-card p {
        color: var(--muted);
        margin: 0;
        line-height: 1.75;
        font-size: 0.94rem;
    }
    .paper-card {
        padding: 1rem;
        border-radius: 20px;
        border: 1px solid var(--stroke);
        background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(246,250,255,0.92));
        box-shadow: 0 8px 22px rgba(38, 52, 74, 0.05);
        margin-bottom: 1rem;
    }
    .paper-card h4 {
        margin: 0 0 0.3rem 0;
        color: var(--ink);
    }
    .paper-meta {
        color: var(--muted);
        font-size: 0.9rem;
        margin-bottom: 0.7rem;
    }
    div[data-testid="stTextArea"] textarea {
        border-radius: 16px !important;
        background: rgba(248, 250, 252, 0.98) !important;
        border: 1px solid rgba(23, 50, 77, 0.12) !important;
        color: var(--ink) !important;
        line-height: 1.7 !important;
    }
    .compare-wrap {
        overflow-x: auto;
        border-radius: 22px;
        border: 1px solid rgba(23, 50, 77, 0.10);
        background: rgba(255,255,255,0.92);
        box-shadow: 0 10px 28px rgba(35, 49, 70, 0.05);
    }
    .compare-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }
    .compare-table col.title { width: 16%; }
    .compare-table col.problem { width: 22%; }
    .compare-table col.method { width: 22%; }
    .compare-table col.datasets { width: 12%; }
    .compare-table col.metrics { width: 10%; }
    .compare-table col.limitations { width: 18%; }
    .compare-table th,
    .compare-table td {
        padding: 14px 12px;
        border-bottom: 1px solid rgba(23, 50, 77, 0.08);
        vertical-align: top;
        text-align: left;
        color: var(--ink);
        font-size: 14px;
        line-height: 1.7;
        word-break: break-word;
        overflow-wrap: anywhere;
    }
    .compare-table th {
        background: rgba(243, 247, 251, 0.98);
        font-size: 15px;
        font-weight: 700;
        position: sticky;
        top: 0;
        z-index: 1;
    }
    .cell-scroll {
        max-height: 180px;
        overflow-y: auto;
        padding-right: 4px;
    }
    </style>
    """


def init_state() -> None:
    defaults = {
        "project_id": "",
        "project_name": "多论文分析与研究空白验证平台",
        "topic": "围绕多篇论文的结构化抽取、横向对比、字段补全与研究空白验证。",
        "target_type": "meeting_outline",
        "papers": [],
        "compare_result": None,
        "field_completions": [],
        "gaps": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


init_state()
st.markdown(app_style(), unsafe_allow_html=True)


def normalize_display_text(value: str) -> str:
    """Lightly clean PDF spacing artifacts for UI display."""

    if not value:
        return ""
    text = str(value).replace("\u00ad", "")
    text = re.sub(r"(?<=[A-Za-z])\-\s+(?=[a-z])", "", text)
    text = re.sub(r"\s+([,.;:!?%)\]])", r"\1", text)
    text = re.sub(r"([([\]])\s+", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_display_lines(values: list[str]) -> list[str]:
    return [cleaned for item in values for cleaned in [normalize_display_text(item)] if cleaned]


def call_api(method: str, url: str, *, timeout: int = 60, show_error: bool = True, **kwargs):
    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
        if response.ok:
            if response.content:
                return response.json()
            return {}
        if show_error:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            st.error(f"请求失败：{detail}")
    except requests.RequestException as exc:
        if show_error:
            st.error(f"请求失败：{exc}")
    return None


BACKEND_URL = st.sidebar.text_input("后端地址", value="http://127.0.0.1:8000")


def clear_project_cache() -> None:
    st.session_state.papers = []
    st.session_state.compare_result = None
    st.session_state.field_completions = []
    st.session_state.gaps = []


def refresh_project_snapshot(show_notice: bool = False) -> None:
    project_id = st.session_state.project_id
    if not project_id:
        return

    papers = call_api("GET", f"{BACKEND_URL}/api/projects/{project_id}/papers", timeout=180, show_error=False)
    compare = call_api("GET", f"{BACKEND_URL}/api/projects/{project_id}/compare", timeout=180, show_error=False)
    completions = call_api("GET", f"{BACKEND_URL}/api/projects/{project_id}/field-completions", timeout=120, show_error=False)
    gaps = call_api("GET", f"{BACKEND_URL}/api/projects/{project_id}/gaps", timeout=120, show_error=False)

    if papers is not None:
        st.session_state.papers = papers.get("papers", [])
    if compare is not None:
        st.session_state.compare_result = compare.get("compare_result")
    if completions is not None:
        st.session_state.field_completions = completions.get("field_completions", [])
    if gaps is not None:
        st.session_state.gaps = gaps.get("gaps", [])
    if show_notice:
        st.success("当前项目数据已同步。")


def render_compare_table(rows: list[dict]) -> None:
    if not rows:
        st.info("当前还没有对比结果。")
        return

    rendered_rows: list[str] = []
    for row in rows:
        title = html.escape(normalize_display_text(row.get("title") or "未命名论文"))
        problem = html.escape(normalize_display_text(row.get("research_problem") or "待补充"))
        method = html.escape(normalize_display_text(row.get("method") or "待补充"))
        datasets = "<br>".join(html.escape(item) for item in normalize_display_lines(row.get("datasets", []))) or "待补充"
        metrics = "<br>".join(html.escape(item) for item in normalize_display_lines(row.get("metrics", []))) or "待补充"
        limitations = "<br>".join(html.escape(item) for item in normalize_display_lines(row.get("limitations", []))) or "待补充"
        rendered_rows.append(
            "<tr>"
            f"<td><div class='cell-scroll'>{title}</div></td>"
            f"<td><div class='cell-scroll'>{problem}</div></td>"
            f"<td><div class='cell-scroll'>{method}</div></td>"
            f"<td><div class='cell-scroll'>{datasets}</div></td>"
            f"<td><div class='cell-scroll'>{metrics}</div></td>"
            f"<td><div class='cell-scroll'>{limitations}</div></td>"
            "</tr>"
        )

    st.markdown(
        "<div class='compare-wrap'><table class='compare-table'>"
        "<colgroup>"
        "<col class='title'><col class='problem'><col class='method'><col class='datasets'><col class='metrics'><col class='limitations'>"
        "</colgroup>"
        "<thead><tr><th>论文题目</th><th>研究问题</th><th>方法描述</th><th>数据集</th><th>评测指标</th><th>局限性</th></tr></thead>"
        f"<tbody>{''.join(rendered_rows)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <div class="hero">
      <h1>多论文分析与研究空白验证平台</h1>
      <p>面向科研场景的多论文分析系统。支持 PDF 上传、结构化抽取、字段补全、跨论文对比、研究空白验证与结果导出。主流程默认不做翻译，先稳定展示原始结果；如需统一中文展示，可手动点击“翻译当前项目结果”。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_col1, metric_col2, metric_col3 = st.columns(3)
with metric_col1:
    st.markdown(
        f"<div class='metric-card'><div class='label'>当前项目</div><div class='value'>{st.session_state.project_id or '未创建'}</div></div>",
        unsafe_allow_html=True,
    )
with metric_col2:
    st.markdown(
        f"<div class='metric-card'><div class='label'>论文数量</div><div class='value'>{len(st.session_state.papers)}</div></div>",
        unsafe_allow_html=True,
    )
with metric_col3:
    st.markdown(
        f"<div class='metric-card'><div class='label'>Gap 候选数</div><div class='value'>{len(st.session_state.gaps)}</div></div>",
        unsafe_allow_html=True,
    )

with st.sidebar:
    st.markdown("### 当前项目")
    st.write(f"项目 ID：`{st.session_state.project_id or '未创建'}`")
    if st.button("同步当前项目数据", use_container_width=True, disabled=not st.session_state.project_id):
        refresh_project_snapshot(show_notice=True)
    if st.button("翻译当前项目结果", use_container_width=True, disabled=not st.session_state.project_id):
        translated = call_api(
            "POST",
            f"{BACKEND_URL}/api/projects/{st.session_state.project_id}/translate-results",
            timeout=600,
        )
        if translated is not None:
            st.session_state.papers = translated.get("translated_papers", [])
            refresh_project_snapshot()
            st.success("当前项目结果已尝试翻译，页面内容已更新。")
    st.caption("主流程先稳定生成结果。需要统一中文展示时，再单独点翻译按钮。")

project_tab, upload_tab, papers_tab, compare_tab, completion_tab, gap_tab, review_tab, export_tab = st.tabs(
    ["项目创建", "论文上传与分析", "论文卡片", "多篇对比", "字段补全", "Gap 验证", "人工确认", "导出结果"]
)

with project_tab:
    st.markdown(
        "<div class='section-card'><h3>新建分析项目</h3><p>建议一个项目对应一组主题接近的论文。这样上传两三篇论文后，后续对比、字段补全和 Gap 验证都会在同一项目内集中展示。</p></div>",
        unsafe_allow_html=True,
    )
    project_name = st.text_input("项目名称", value=st.session_state.project_name)
    topic = st.text_area("研究主题说明", value=st.session_state.topic, height=110)
    target_type_label = st.selectbox("输出目标", list(TARGET_TYPE_LABELS.keys()), index=0)
    if st.button("创建项目", use_container_width=True):
        data = call_api(
            "POST",
            f"{BACKEND_URL}/api/projects",
            json={
                "project_name": project_name,
                "topic": topic,
                "target_type": TARGET_TYPE_LABELS[target_type_label],
            },
            timeout=30,
        )
        if data:
            st.session_state.project_id = data["project_id"]
            st.session_state.project_name = project_name
            st.session_state.topic = topic
            st.session_state.target_type = TARGET_TYPE_LABELS[target_type_label]
            clear_project_cache()
            st.success(f"项目已创建：{st.session_state.project_id}")

with upload_tab:
    st.markdown(
        "<div class='section-card'><h3>上传论文并启动分析</h3><p>先点“上传论文”，再点“开始分析”。上传成功后不会自动触发翻译，分析完成后会自动同步一次结果页面。</p></div>",
        unsafe_allow_html=True,
    )
    uploaded_files = st.file_uploader("选择多篇 PDF 论文", type=["pdf"], accept_multiple_files=True)
    if st.button("上传论文", disabled=not st.session_state.project_id):
        if not uploaded_files:
            st.warning("请先选择至少一个 PDF 文件。")
        else:
            files = [("files", (item.name, item.getvalue(), "application/pdf")) for item in uploaded_files]
            data = call_api(
                "POST",
                f"{BACKEND_URL}/api/projects/{st.session_state.project_id}/papers/upload",
                files=files,
                timeout=180,
            )
            if data:
                clear_project_cache()
                st.success(f"上传成功，共 {len(data.get('paper_ids', []))} 篇论文。现在可以直接点击“开始分析”。")

    option_col1, option_col2 = st.columns(2)
    with option_col1:
        enable_gap_analysis = st.checkbox("启用研究空白验证", value=True)
    with option_col2:
        enable_external_search = st.checkbox("允许外部补充检索", value=False)

    if st.button("开始分析", disabled=not st.session_state.project_id, use_container_width=True):
        data = call_api(
            "POST",
            f"{BACKEND_URL}/api/projects/{st.session_state.project_id}/analyze",
            json={
                "enable_gap_analysis": enable_gap_analysis,
                "enable_external_search": enable_external_search,
            },
            timeout=1800,
        )
        if data:
            refresh_project_snapshot()
            st.success("分析流程已完成，页面结果已更新。")

with papers_tab:
    st.markdown(
        "<div class='section-card'><h3>论文结构化卡片</h3><p>这里展示当前项目下每篇论文的结构化结果。页面先稳定展示英文或中英混合内容；如果需要统一中文，可在左侧点击“翻译当前项目结果”。</p></div>",
        unsafe_allow_html=True,
    )
    if not st.session_state.papers:
        st.info("当前还没有论文卡片，请先上传论文并完成分析，或点击左侧“同步当前项目数据”。")
    for paper in st.session_state.papers:
        st.markdown(
            f"<div class='paper-card'><h4>{html.escape(normalize_display_text(paper.get('title') or '未命名论文'))}</h4><div class='paper-meta'>论文 ID：{paper.get('paper_id')} | 年份：{paper.get('year') or '未识别'}</div></div>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            st.text_area("研究问题", value=normalize_display_text(paper.get("research_problem") or "待补充"), height=130, key=f"problem_{paper['paper_id']}")
            st.text_area("方法概述", value=normalize_display_text(paper.get("method") or "待补充"), height=140, key=f"method_{paper['paper_id']}")
            st.text_area("主要结果", value=normalize_display_text(paper.get("main_results") or "待补充"), height=130, key=f"results_{paper['paper_id']}")
        with col2:
            st.text_area("数据集", value="\n".join(normalize_display_lines(paper.get("datasets", []))) or "待补充", height=110, key=f"datasets_{paper['paper_id']}")
            st.text_area("评测指标", value="\n".join(normalize_display_lines(paper.get("metrics", []))) or "待补充", height=100, key=f"metrics_{paper['paper_id']}")
            st.text_area("局限性", value="\n".join(normalize_display_lines(paper.get("limitations", []))) or "待补充", height=120, key=f"limitations_{paper['paper_id']}")
            st.text_area("未来工作", value="\n".join(normalize_display_lines(paper.get("future_work", []))) or "待补充", height=110, key=f"future_{paper['paper_id']}")
        if paper.get("warnings"):
            st.warning("；".join(normalize_display_lines(paper["warnings"])))

with compare_tab:
    st.markdown(
        "<div class='section-card'><h3>多篇论文横向对比</h3><p>这里保留横向表格形式，但单元格内容会自动换行，且内部有固定高度和滚动区域，不会再被一条超长局限性把整页撑满。</p></div>",
        unsafe_allow_html=True,
    )
    compare_result = st.session_state.compare_result
    if not compare_result:
        st.info("当前还没有对比结果，请先完成分析或点击同步。")
    else:
        st.text_area("趋势总结", value=normalize_display_text(compare_result.get("trend_summary") or "待补充"), height=110, key="trend_summary")
        render_compare_table(compare_result.get("rows", []))

with completion_tab:
    st.markdown(
        "<div class='section-card'><h3>字段补全结果</h3><p>这里展示字段补全前后差异、检索查询和证据片段。需要人工确认的条目会同时出现在人工确认页。</p></div>",
        unsafe_allow_html=True,
    )
    if not st.session_state.field_completions:
        st.info("当前没有字段补全记录。")
    for item in st.session_state.field_completions:
        label = FIELD_LABELS.get(item.get("field_name"), item.get("field_name"))
        st.markdown(
            f"<div class='paper-card'><h4>{item.get('paper_id')} · {label}</h4><div class='paper-meta'>状态：{item.get('fill_status')} | 需人工确认：{'是' if item.get('requires_human_review') else '否'}</div></div>",
            unsafe_allow_html=True,
        )
        left, right = st.columns(2)
        original = item.get("original_value")
        if isinstance(original, list):
            original = "\n".join(normalize_display_lines(original))
        else:
            original = normalize_display_text(original or "")
        filled = item.get("filled_value")
        if isinstance(filled, list):
            filled = "\n".join(normalize_display_lines(filled))
        else:
            filled = normalize_display_text(filled or "")
        with left:
            st.text_area("补全前", value=original or "空值", height=110, key=f"before_{item['paper_id']}_{item['field_name']}")
        with right:
            st.text_area("补全后", value=filled or "空值", height=110, key=f"after_{item['paper_id']}_{item['field_name']}")
        st.text_area("检索查询", value=normalize_display_text(item.get("retrieval_query") or "无"), height=70, key=f"query_{item['paper_id']}_{item['field_name']}")
        evidence_text = "\n\n".join(
            f"第 {ev['page_start']}-{ev['page_end']} 页 | {ev['section']}\n{normalize_display_text(ev['content'][:220])}"
            for ev in item.get("candidate_evidence", [])
        ) or "暂无证据"
        st.text_area("候选证据", value=evidence_text, height=170, key=f"evidence_{item['paper_id']}_{item['field_name']}")

with gap_tab:
    st.markdown(
        "<div class='section-card'><h3>研究空白候选验证</h3><p>这里展示支持证据、反证和最终验证结果。它们是候选结论，不会直接替代人工判断。</p></div>",
        unsafe_allow_html=True,
    )
    if not st.session_state.gaps:
        st.info("当前没有 Gap 候选。")
    for gap in st.session_state.gaps:
        st.markdown(
            f"<div class='paper-card'><h4>{html.escape(normalize_display_text(gap.get('statement') or '未命名候选'))}</h4><div class='paper-meta'>验证结果：{normalize_display_text(gap.get('validation_result') or '待验证')} | 覆盖论文数：{gap.get('coverage_count', 0)} | 置信度：{gap.get('confidence', 0)}</div></div>",
            unsafe_allow_html=True,
        )
        left, right = st.columns(2)
        support_text = "\n\n".join(
            f"{ev['paper_id']} | 第 {ev['page_start']}-{ev['page_end']} 页\n{normalize_display_text(ev['content'][:220])}"
            for ev in gap.get("supporting_evidence", [])
        ) or "暂无支持证据"
        counter_text = "\n\n".join(
            f"{ev['paper_id']} | 第 {ev['page_start']}-{ev['page_end']} 页\n{normalize_display_text(ev['content'][:220])}"
            for ev in gap.get("counter_evidence", [])
        ) or "暂无反证或冲突证据"
        with left:
            st.text_area("支持证据", value=support_text, height=180, key=f"gap_support_{gap['gap_id']}")
        with right:
            st.text_area("反证 / 冲突证据", value=counter_text, height=180, key=f"gap_counter_{gap['gap_id']}")
        st.text_area("建议方向", value=normalize_display_text(gap.get("suggested_direction") or "待补充"), height=90, key=f"gap_direction_{gap['gap_id']}")

with review_tab:
    st.markdown(
        "<div class='section-card'><h3>人工确认</h3><p>这里集中处理高风险字段补全结果和高风险 Gap 候选。你可以保留、删除，或者先编辑再保存。</p></div>",
        unsafe_allow_html=True,
    )
    review_col1, review_col2 = st.columns(2)

    with review_col1:
        st.markdown("### 字段补全审核")
        pending_items = [item for item in st.session_state.field_completions if item.get("requires_human_review")]
        if not pending_items:
            st.info("当前没有需要人工确认的字段补全结果。")
        for item in pending_items:
            field_label = FIELD_LABELS.get(item.get("field_name"), item.get("field_name"))
            st.write(f"**{item.get('paper_id')} / {field_label}**")
            current_value = item.get("filled_value")
            if isinstance(current_value, list):
                current_value = "\n".join(normalize_display_lines(current_value))
            else:
                current_value = normalize_display_text(current_value or "")
            edited_value = st.text_area(
                "编辑字段值",
                value=current_value or "",
                key=f"field_edit_{item['paper_id']}_{item['field_name']}",
                height=100,
            )
            c1, c2, c3 = st.columns(3)
            if c1.button("保留", key=f"field_keep_{item['paper_id']}_{item['field_name']}"):
                call_api(
                    "POST",
                    f"{BACKEND_URL}/api/projects/{st.session_state.project_id}/field-completions/review",
                    json={"paper_id": item["paper_id"], "field_name": item["field_name"], "action": "approve"},
                )
                refresh_project_snapshot()
            if c2.button("删除", key=f"field_delete_{item['paper_id']}_{item['field_name']}"):
                call_api(
                    "POST",
                    f"{BACKEND_URL}/api/projects/{st.session_state.project_id}/field-completions/review",
                    json={"paper_id": item["paper_id"], "field_name": item["field_name"], "action": "reject"},
                )
                refresh_project_snapshot()
            if c3.button("编辑保存", key=f"field_edit_save_{item['paper_id']}_{item['field_name']}"):
                value = [part.strip() for part in edited_value.splitlines() if part.strip()]
                call_api(
                    "POST",
                    f"{BACKEND_URL}/api/projects/{st.session_state.project_id}/field-completions/review",
                    json={
                        "paper_id": item["paper_id"],
                        "field_name": item["field_name"],
                        "action": "edit",
                        "edited_value": value,
                    },
                )
                refresh_project_snapshot()

    with review_col2:
        st.markdown("### 研究空白审核")
        pending_gaps = [gap for gap in st.session_state.gaps if gap.get("requires_human_review") or gap.get("status") == "pending"]
        if not pending_gaps:
            st.info("当前没有需要人工确认的研究空白候选。")
        for gap in pending_gaps:
            st.write(f"**{normalize_display_text(gap.get('statement') or '')}**")
            edited_statement = st.text_area("编辑候选结论", value=normalize_display_text(gap.get("statement") or ""), key=f"gap_statement_{gap['gap_id']}", height=100)
            edited_direction = st.text_area("编辑建议方向", value=normalize_display_text(gap.get("suggested_direction") or ""), key=f"gap_direction_edit_{gap['gap_id']}", height=90)
            g1, g2, g3 = st.columns(3)
            if g1.button("保留", key=f"gap_keep_{gap['gap_id']}"):
                call_api(
                    "POST",
                    f"{BACKEND_URL}/api/projects/{st.session_state.project_id}/gaps/review",
                    json={"gap_id": gap["gap_id"], "action": "approve"},
                )
                refresh_project_snapshot()
            if g2.button("删除", key=f"gap_delete_{gap['gap_id']}"):
                call_api(
                    "POST",
                    f"{BACKEND_URL}/api/projects/{st.session_state.project_id}/gaps/review",
                    json={"gap_id": gap["gap_id"], "action": "reject"},
                )
                refresh_project_snapshot()
            if g3.button("编辑保存", key=f"gap_edit_save_{gap['gap_id']}"):
                call_api(
                    "POST",
                    f"{BACKEND_URL}/api/projects/{st.session_state.project_id}/gaps/review",
                    json={
                        "gap_id": gap["gap_id"],
                        "action": "edit",
                        "edited_statement": edited_statement,
                        "edited_suggested_direction": edited_direction,
                    },
                )
                refresh_project_snapshot()

with export_tab:
    st.markdown(
        "<div class='section-card'><h3>导出结果</h3><p>默认会沿用项目创建时选择的输出目标。只有当你这一次想临时换一个导出类型时，才需要手动切换。</p></div>",
        unsafe_allow_html=True,
    )
    reverse_target_labels = {value: key for key, value in TARGET_TYPE_LABELS.items()}
    current_target_type = st.session_state.get("target_type", "meeting_outline")
    current_target_label = reverse_target_labels.get(current_target_type, "组会汇报")
    st.info(f"当前项目默认导出目标：{current_target_label}")

    use_custom_export = st.checkbox("临时切换导出类型", value=False)
    export_type = current_target_type
    if use_custom_export:
        default_label = reverse_target_labels.get(current_target_type, "组会汇报")
        export_labels = list(EXPORT_TYPE_LABELS.keys())
        default_index = export_labels.index(default_label) if default_label in export_labels else 1
        export_type_label = st.selectbox("导出类型", export_labels, index=default_index)
        export_type = EXPORT_TYPE_LABELS[export_type_label]

    button_label = "导出当前目标结果" if not use_custom_export else "导出当前选择结果"
    if st.button(button_label, disabled=not st.session_state.project_id, use_container_width=True):
        data = call_api(
            "POST",
            f"{BACKEND_URL}/api/projects/{st.session_state.project_id}/export",
            json={"export_type": export_type},
            timeout=180,
        )
        if data:
            export_data = data["export"]
            st.success(f"已导出到：{export_data['file_path']}")
            st.text_area("导出内容预览", value=normalize_display_text(export_data.get("content") or ""), height=320, key="export_preview")
