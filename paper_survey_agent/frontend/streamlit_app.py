from __future__ import annotations

import html
import re

import requests
import streamlit as st

st.set_page_config(page_title="\u79d1\u7814\u6587\u732e\u591a\u7bc7\u6bd4\u8f83\u4e0e\u7814\u7a76\u7a7a\u767d\u5206\u6790\u5e73\u53f0", layout="wide")

TARGET_TYPE_LABELS = {
    "\u7ec4\u4f1a\u6c47\u62a5": "meeting_outline",
    "\u8bba\u6587\u7efc\u8ff0": "survey",
    "\u7814\u7a76\u7a7a\u767d\u5206\u6790": "gap_analysis",
}
REVERSE_TARGET_TYPE_LABELS = {value: key for key, value in TARGET_TYPE_LABELS.items()}

GAP_VALIDATION_LEVEL_LABELS = {"\u8f7b\u91cf\u9a8c\u8bc1": "light", "\u4e25\u683c\u9a8c\u8bc1": "strict", "\u5173\u95ed\u9a8c\u8bc1": "off"}
REVERSE_GAP_VALIDATION_LEVEL_LABELS = {value: key for key, value in GAP_VALIDATION_LEVEL_LABELS.items()}

EXPORT_TYPE_LABELS = {
    "\u8bba\u6587\u7efc\u8ff0": "survey",
    "\u7ec4\u4f1a\u6c47\u62a5": "meeting_outline",
    "\u7814\u7a76\u7a7a\u767d\u5206\u6790": "gap_analysis",
    "\u5bf9\u6bd4\u8868": "compare_table",
}

FIELD_LABELS = {
    "datasets": "\u6570\u636e\u96c6",
    "metrics": "\u8bc4\u6d4b\u6307\u6807",
    "limitations": "\u5c40\u9650\u6027",
    "future_work": "\u672a\u6765\u5de5\u4f5c",
}

FOCUS_DIMENSION_OPTIONS = {
    "\u65b9\u6cd5\u8bbe\u8ba1": "methods",
    "\u6570\u636e\u96c6": "datasets",
    "\u8bc4\u6d4b\u6307\u6807": "metrics",
    "\u5c40\u9650\u6027": "limitations",
    "\u672a\u6765\u5de5\u4f5c": "future_work",
    "\u7814\u7a76\u7a7a\u767d": "research_gap",
    "\u6548\u7387\u4e0e\u6210\u672c": "efficiency",
}
REVERSE_FOCUS_DIMENSION_OPTIONS = {value: key for key, value in FOCUS_DIMENSION_OPTIONS.items()}


def app_style() -> str:
    return """
    <style>
    :root {
        --bg: linear-gradient(135deg, #f7f1e7 0%, #edf3fb 52%, #f8fbff 100%);
        --panel: rgba(255, 255, 255, 0.84);
        --stroke: rgba(23, 50, 77, 0.10);
        --ink: #18324c;
        --muted: #607287;
    }
    .stApp { background: var(--bg); }
    .block-container { max-width: 1260px; padding-top: 1.6rem; padding-bottom: 3rem; }
    .hero {
        padding: 1.9rem 2.1rem;
        border-radius: 28px;
        background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(255,247,241,0.92));
        border: 1px solid var(--stroke);
        box-shadow: 0 18px 40px rgba(27, 44, 67, 0.08);
        margin-bottom: 1rem;
    }
    .hero h1 { color: var(--ink); font-size: 2.08rem; margin-bottom: 0.4rem; }
    .hero p { color: var(--muted); line-height: 1.75; margin: 0; }
    .metric-card {
        padding: 1rem 1.15rem;
        background: var(--panel);
        border-radius: 22px;
        border: 1px solid var(--stroke);
        box-shadow: 0 10px 30px rgba(33, 49, 72, 0.06);
        min-height: 108px;
    }
    .metric-card .label { color: var(--muted); font-size: 0.92rem; }
    .metric-card .value { margin-top: 0.35rem; color: var(--ink); font-size: 1.45rem; font-weight: 700; word-break: break-word; }
    .section-card {
        background: rgba(255,255,255,0.88);
        border-radius: 24px;
        padding: 1rem 1.2rem;
        border: 1px solid var(--stroke);
        box-shadow: 0 10px 28px rgba(35, 48, 69, 0.05);
        margin-bottom: 1rem;
    }
    .section-card h3 { color: var(--ink); margin: 0 0 0.45rem 0; font-size: 1.08rem; }
    .section-card p { color: var(--muted); margin: 0; line-height: 1.75; font-size: 0.94rem; }
    .paper-card {
        padding: 1rem;
        border-radius: 20px;
        border: 1px solid var(--stroke);
        background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(246,250,255,0.92));
        box-shadow: 0 8px 22px rgba(38, 52, 74, 0.05);
        margin-bottom: 1rem;
    }
    .paper-card h4 { margin: 0 0 0.3rem 0; color: var(--ink); }
    .paper-meta { color: var(--muted); font-size: 0.9rem; margin-bottom: 0.7rem; }
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
    .compare-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .compare-table col.title { width: 16%; }
    .compare-table col.problem { width: 22%; }
    .compare-table col.method { width: 22%; }
    .compare-table col.datasets { width: 12%; }
    .compare-table col.metrics { width: 10%; }
    .compare-table col.limitations { width: 18%; }
    .compare-table th, .compare-table td {
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
    .cell-scroll { max-height: 180px; overflow-y: auto; padding-right: 4px; }
    </style>
    """


def init_state() -> None:
    defaults = {
        "project_id": "",
        "project_name": "\u79d1\u7814\u6587\u732e\u591a\u7bc7\u6bd4\u8f83\u4e0e\u7814\u7a76\u7a7a\u767d\u5206\u6790\u5e73\u53f0",
        "topic": "\u56f4\u7ed5\u591a\u7bc7\u8bba\u6587\u7684\u7ed3\u6784\u5316\u62bd\u53d6\u3001\u6a2a\u5411\u5bf9\u6bd4\u3001\u5b57\u6bb5\u8865\u5168\u4e0e\u7814\u7a76\u7a7a\u767d\u9a8c\u8bc1\u3002",
        "target_type": "meeting_outline",
        "focus_dimensions": ["methods", "research_gap"],
        "user_requirements": "",
        "gap_validation_level": "light",
        "projects": [],
        "papers": [],
        "compare_result": None,
        "field_completions": [],
        "gaps": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


init_state()
st.session_state.setdefault("focus_dimensions", ["methods", "research_gap"])
st.session_state.setdefault("user_requirements", "")
st.session_state.setdefault("gap_validation_level", "light")
st.markdown(app_style(), unsafe_allow_html=True)


def normalize_display_text(value: str) -> str:
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



def apply_project_summary(summary: dict) -> None:
    st.session_state.project_id = summary.get("project_id", "")
    st.session_state.project_name = summary.get("project_name", st.session_state.project_name)
    st.session_state.topic = summary.get("topic", st.session_state.topic)
    st.session_state.target_type = summary.get("target_type", st.session_state.target_type)
    st.session_state.focus_dimensions = summary.get("focus_dimensions", st.session_state.focus_dimensions)
    st.session_state.user_requirements = summary.get("user_requirements", st.session_state.user_requirements)
    st.session_state.gap_validation_level = summary.get("gap_validation_level", st.session_state.gap_validation_level)



def find_project_summary(project_id: str) -> dict | None:
    return next((item for item in st.session_state.projects if item.get("project_id") == project_id), None)



def refresh_project_catalog(show_notice: bool = False) -> None:
    data = call_api("GET", f"{BACKEND_URL}/api/projects", timeout=45, show_error=False)
    if data is not None:
        st.session_state.projects = data.get("projects", [])
        if show_notice:
            st.success("项目列表已刷新。")



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


refresh_project_catalog()
if st.session_state.projects and not st.session_state.project_id:
    apply_project_summary(st.session_state.projects[0])
    refresh_project_snapshot()
elif st.session_state.project_id:
    summary = find_project_summary(st.session_state.project_id)
    if summary is not None:
        apply_project_summary(summary)



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
      <p>面向科研场景的多论文分析系统。支持项目创建、历史项目切换、PDF 上传、结构化抽取、字段补全、跨论文对比、研究空白验证与结果导出。系统已支持全局论文复用：同一篇 PDF 在不同项目中不会重复入库，删除项目时会按引用关系决定是否清理论文资产和向量索引。</p>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_col1, metric_col2, metric_col3 = st.columns(3)
with metric_col1:
    st.markdown(
        f"<div class='metric-card'><div class='label'>当前项目</div><div class='value'>{st.session_state.project_id or '未选择'}</div></div>",
        unsafe_allow_html=True,
    )
with metric_col2:
    st.markdown(
        f"<div class='metric-card'><div class='label'>项目内论文数</div><div class='value'>{len(st.session_state.papers)}</div></div>",
        unsafe_allow_html=True,
    )
with metric_col3:
    st.markdown(
        f"<div class='metric-card'><div class='label'>Gap 候选数</div><div class='value'>{len(st.session_state.gaps)}</div></div>",
        unsafe_allow_html=True,
    )

with st.sidebar:
    st.markdown("### 项目管理")
    if st.button("刷新项目列表", use_container_width=True):
        refresh_project_catalog(show_notice=True)

    projects = st.session_state.projects
    if projects:
        project_options = {f"{item['project_name']} · {item['paper_count']}篇": item for item in projects}
        project_labels = list(project_options.keys())
        current_index = 0
        for index, item in enumerate(projects):
            if item.get("project_id") == st.session_state.project_id:
                current_index = index
                break
        selected_label = st.selectbox("历史项目", project_labels, index=current_index)
        selected_summary = project_options[selected_label]
        if st.button("切换到所选项目", use_container_width=True):
            apply_project_summary(selected_summary)
            clear_project_cache()
            refresh_project_snapshot(show_notice=True)
    else:
        st.caption("当前还没有历史项目。")

    confirm_delete = st.checkbox("确认删除当前项目", value=False, disabled=not st.session_state.project_id)
    if st.button("删除当前项目", use_container_width=True, disabled=not st.session_state.project_id or not confirm_delete):
        deleted = call_api("DELETE", f"{BACKEND_URL}/api/projects/{st.session_state.project_id}", timeout=120)
        if deleted is not None:
            removed_id = st.session_state.project_id
            clear_project_cache()
            st.session_state.project_id = ""
            st.session_state.project_name = "多论文分析与研究空白验证平台"
            st.session_state.topic = "围绕多篇论文的结构化抽取、横向对比、字段补全与研究空白验证。"
            st.session_state.target_type = "meeting_outline"
            st.session_state.focus_dimensions = ["methods", "research_gap"]
            st.session_state.user_requirements = ""
            st.session_state.gap_validation_level = "light"
            refresh_project_catalog()
            if st.session_state.projects:
                apply_project_summary(st.session_state.projects[0])
                refresh_project_snapshot()
            st.success(f"项目 {removed_id} 已删除。")

    st.markdown("### 当前项目")
    st.write(f"项目 ID：`{st.session_state.project_id or '未选择'}`")
    current_summary = find_project_summary(st.session_state.project_id) if st.session_state.project_id else None
    if current_summary is not None:
        st.caption(f"项目内论文数：{current_summary.get('paper_count', 0)}")

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
    st.caption("主流程默认不翻译。需要统一中文时，再单独点击翻译按钮。")

project_tab, upload_tab, papers_tab, compare_tab, completion_tab, gap_tab, review_tab, export_tab = st.tabs(
    ["项目创建", "论文上传与分析", "论文卡片", "多篇对比", "字段补全", "Gap 验证", "人工确认", "导出结果"]
)

with project_tab:
    st.subheader("\u65b0\u5efa\u5206\u6790\u9879\u76ee")
    project_name = st.text_input("\u9879\u76ee\u540d\u79f0", value=st.session_state.project_name)
    topic = st.text_area("\u7814\u7a76\u4e3b\u9898\u8bf4\u660e", value=st.session_state.topic, height=110)
    target_labels = list(TARGET_TYPE_LABELS.keys())
    default_label = REVERSE_TARGET_TYPE_LABELS.get(st.session_state.target_type, "\u7ec4\u4f1a\u6c47\u62a5")
    target_type_label = st.selectbox("\u8f93\u51fa\u76ee\u6807", target_labels, index=target_labels.index(default_label))
    target_type_value = TARGET_TYPE_LABELS[target_type_label]
    recommended_gap_level = "strict" if target_type_value == "gap_analysis" else "light"
    current_gap_level = st.session_state.gap_validation_level or recommended_gap_level
    if current_gap_level not in REVERSE_GAP_VALIDATION_LEVEL_LABELS:
        current_gap_level = recommended_gap_level
    gap_level_label = st.selectbox(
        "Gap \u9a8c\u8bc1\u5f3a\u5ea6",
        list(GAP_VALIDATION_LEVEL_LABELS.keys()),
        index=list(GAP_VALIDATION_LEVEL_LABELS.keys()).index(REVERSE_GAP_VALIDATION_LEVEL_LABELS.get(current_gap_level, REVERSE_GAP_VALIDATION_LEVEL_LABELS[recommended_gap_level])),
        help="\u7efc\u8ff0\u548c\u7ec4\u4f1a\u6c47\u62a5\u9ed8\u8ba4\u4f7f\u7528\u8f7b\u91cf\u9a8c\u8bc1\uff0c\u7814\u7a76\u7a7a\u767d\u5206\u6790\u9ed8\u8ba4\u4f7f\u7528\u4e25\u683c\u9a8c\u8bc1\uff1b\u4f60\u4e5f\u53ef\u4ee5\u624b\u52a8\u8986\u76d6\u3002",
    )

    default_focus_labels = [
        REVERSE_FOCUS_DIMENSION_OPTIONS[item]
        for item in st.session_state.focus_dimensions
        if item in REVERSE_FOCUS_DIMENSION_OPTIONS
    ]
    selected_focus_labels = st.multiselect(
        "\u91cd\u70b9\u5173\u6ce8",
        list(FOCUS_DIMENSION_OPTIONS.keys()),
        default=default_focus_labels,
        help="\u7cfb\u7edf\u4f1a\u5728\u591a\u7bc7\u5bf9\u6bd4\u3001Research Gap \u5019\u9009\u548c\u5bfc\u51fa\u7ed3\u679c\u4e2d\u4f18\u5148\u5f3a\u8c03\u8fd9\u4e9b\u7ef4\u5ea6\u3002",
    )
    user_requirements = st.text_area(
        "\u7528\u6237\u989d\u5916\u8981\u6c42",
        value=st.session_state.user_requirements,
        height=90,
        placeholder="\u4f8b\u5982\uff1a\u66f4\u5173\u6ce8\u6cdb\u5316\u80fd\u529b\u3001\u8de8\u6570\u636e\u96c6\u8868\u73b0\u548c\u90e8\u7f72\u53ef\u884c\u6027\u3002",
    )

    if st.button("\u521b\u5efa\u9879\u76ee", use_container_width=True):
        focus_dimensions = [FOCUS_DIMENSION_OPTIONS[label] for label in selected_focus_labels]
        data = call_api(
            "POST",
            f"{BACKEND_URL}/api/projects",
            json={
                "project_name": project_name,
                "topic": topic,
                "target_type": TARGET_TYPE_LABELS[target_type_label],
                "focus_dimensions": focus_dimensions,
                "user_requirements": user_requirements,
                "gap_validation_level": GAP_VALIDATION_LEVEL_LABELS[gap_level_label],
            },
            timeout=30,
        )
        if data:
            st.session_state.project_id = data["project_id"]
            st.session_state.project_name = project_name
            st.session_state.topic = topic
            st.session_state.target_type = TARGET_TYPE_LABELS[target_type_label]
            st.session_state.focus_dimensions = focus_dimensions
            st.session_state.user_requirements = user_requirements
            st.session_state.gap_validation_level = GAP_VALIDATION_LEVEL_LABELS[gap_level_label]
            clear_project_cache()
            refresh_project_catalog()
            st.success(f"\u9879\u76ee\u5df2\u521b\u5efa\uff1a{st.session_state.project_id}")

with upload_tab:
    st.markdown(
        "<div class='section-card'><h3>上传论文并启动分析</h3><p>上传时会先做全局去重，再把论文关联到当前项目。也就是说，同一篇论文跨项目复用时不会重复存 PDF、chunk 和向量。</p></div>",
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
                timeout=240,
            )
            if data:
                clear_project_cache()
                refresh_project_catalog()
                new_count = len(data.get("newly_stored_paper_ids", []))
                reused_count = len(data.get("reused_paper_ids", []))
                linked_count = len(data.get("paper_ids", []))
                st.success(f"上传完成：新增入库 {new_count} 篇，复用已有论文 {reused_count} 篇，当前项目新增关联 {linked_count} 篇。")

    option_col1, option_col2 = st.columns(2)
    with option_col1:
        run_recommended_gap_level = "strict" if st.session_state.target_type == "gap_analysis" else "light"
        run_current_gap_level = st.session_state.get("gap_validation_level", run_recommended_gap_level) or run_recommended_gap_level
        if run_current_gap_level not in REVERSE_GAP_VALIDATION_LEVEL_LABELS:
            run_current_gap_level = run_recommended_gap_level
        run_gap_level_label = st.selectbox(
            "本次分析的 Gap 验证强度",
            list(GAP_VALIDATION_LEVEL_LABELS.keys()),
            index=list(GAP_VALIDATION_LEVEL_LABELS.keys()).index(REVERSE_GAP_VALIDATION_LEVEL_LABELS.get(run_current_gap_level, REVERSE_GAP_VALIDATION_LEVEL_LABELS[run_recommended_gap_level])),
            help="三类任务都会生成 gap candidates；这里控制的是本次运行采用 off / light / strict 哪一级验证。",
        )
    with option_col2:
        enable_external_search = st.checkbox("允许外部补充检索", value=False)
    if st.button("开始分析", disabled=not st.session_state.project_id, use_container_width=True):
        data = call_api(
            "POST",
            f"{BACKEND_URL}/api/projects/{st.session_state.project_id}/analyze",
            json={
                "gap_validation_level": GAP_VALIDATION_LEVEL_LABELS[run_gap_level_label],
                "enable_external_search": enable_external_search,
            },
            timeout=1800,
        )
        if data:
            st.session_state.gap_validation_level = GAP_VALIDATION_LEVEL_LABELS[run_gap_level_label]
            refresh_project_snapshot()
            refresh_project_catalog()
            st.success("分析流程已完成，页面结果已更新。")

with papers_tab:
    st.markdown(
        "<div class='section-card'><h3>论文结构化卡片</h3><p>这里展示当前项目下每篇论文的统一结构化结果。翻译不是主流程必经步骤，因此默认先显示原始语言；如果要统一中文，再点击左侧翻译按钮。</p></div>",
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
        "<div class='section-card'><h3>多篇论文横向对比</h3><p>这里保留横向表格形式。单元格固定高度、内部滚动，适合直接查看长段落而不会把整页撑满。</p></div>",
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
        "<div class='section-card'><h3>字段补全结果</h3><p>这里展示字段补全前后结果、检索查询与证据片段。项目删除时，这些项目级记录会一起删除；但若论文还被其他项目引用，其论文向量不会被误删。</p></div>",
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
    current_target_type = st.session_state.get("target_type", "meeting_outline")
    current_target_label = REVERSE_TARGET_TYPE_LABELS.get(current_target_type, "组会汇报")
    st.info(f"当前项目默认导出目标：{current_target_label}")

    use_custom_export = st.checkbox("临时切换导出类型", value=False)
    export_type = current_target_type
    if use_custom_export:
        export_labels = list(EXPORT_TYPE_LABELS.keys())
        default_label = REVERSE_TARGET_TYPE_LABELS.get(current_target_type, "组会汇报")
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




