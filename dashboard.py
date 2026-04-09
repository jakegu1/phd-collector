"""Streamlit dashboard for PhD Project Collector."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import html as html_mod
import urllib.parse
import re
import io

from sqlalchemy import create_engine, func, delete
from sqlalchemy.orm import sessionmaker

from models import PhDProject, Bookmark, Base, init_db
from config import DB_URL
from collector import PhDCollector


def _clean_text(s: str) -> str:
    """Remove surrogate characters that break protobuf/UTF-8 encoding."""
    return s.encode("utf-8", errors="replace").decode("utf-8")


def _parse_deadline_urgency(deadline_str: str) -> str:
    """Parse deadline string and return urgency label with color indicator."""
    if not deadline_str or deadline_str == "nan" or pd.isna(deadline_str):
        return ""
    try:
        clean = re.sub(r"\s*\(.*?\)", "", str(deadline_str)).strip()
        clean = re.sub(r"\s*-\s*\d{1,2}:\d{2}$", "", clean).strip()
        dt = pd.to_datetime(clean, dayfirst=True, format="mixed")
        days = (dt - pd.Timestamp.now()).days
        if days < 0:
            return "\u26ab Expired"
        elif days <= 7:
            return f"\U0001f534 {days}d"
        elif days <= 30:
            return f"\U0001f7e1 {days}d"
        else:
            return f"\U0001f7e2 {days}d"
    except Exception:
        return ""


def _load_bookmarks(engine) -> set:
    """Load bookmarked project IDs from DB."""
    Base.metadata.create_all(engine, tables=[Bookmark.__table__], checkfirst=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        ids = {b.project_id for b in session.query(Bookmark).all()}
        return ids
    finally:
        session.close()


def _toggle_bookmark(engine, project_id: int) -> bool:
    """Toggle bookmark for a project. Returns new bookmark state."""
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        existing = session.query(Bookmark).filter_by(project_id=project_id).first()
        if existing:
            session.delete(existing)
            session.commit()
            return False
        else:
            session.add(Bookmark(project_id=project_id))
            session.commit()
            return True
    finally:
        session.close()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PhD项目收集器",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_resource
def get_engine():
    init_db()
    return create_engine(DB_URL)


def load_projects(engine) -> pd.DataFrame:
    """Load all projects into a DataFrame."""
    query = "SELECT * FROM phd_projects ORDER BY collected_at DESC"
    df = pd.read_sql(query, engine)
    return df


def format_funding(val: str) -> str:
    """Translate funding type to Chinese labels."""
    mapping = {
        "fully_funded": "全奖",
        "csc": "CSC",
        "rolling": "Rolling",
        "position": "岗位制",
        "unknown": "未知",
    }
    if not val:
        return "未知"
    parts = [mapping.get(v.strip(), v.strip()) for v in val.split(",")]
    return " / ".join(parts)


def _build_prompt(sel) -> str:
    """Build the default AI prompt for a project row."""
    project_url = sel.get("url", "")
    return (
        f"请访问以下PhD项目链接，了解项目详情，然后模仿下面的风格撰写一篇小红书推文：\n\n"
        f"项目链接：{project_url}\n\n"
        f"已知信息：\n"
        f"- 标题：{sel.get('title', '')}\n"
        f"- 大学：{sel.get('university', '')}\n"
        f"- 国家/地区：{sel.get('country', '')} ({sel.get('region_cn', '')})\n"
        f"- 学科：{sel.get('discipline', '')}\n"
        f"- 截止时间：{sel.get('deadline', '')}\n"
        f"- 资助类型：{format_funding(sel.get('funding_type', ''))}\n\n"
        f"请按以下风格撰写推文（包含emoji、分段、亮点列举）：\n"
        f"标题格式：[对应国家国旗emoji] + 大学名 + 博士项目招生更新！\n"
        f"内容包括：学校亮点、资助待遇、热门项目一览、申请贴士、适合人群\n"
        f"语气活泼、信息丰富，适合小红书发布。"
    )


def _doubao_button_html(prompt_text: str) -> str:
    """Return pure-ASCII HTML for the copy+open button."""
    doubao_url = "https://www.doubao.com/chat/"
    safe = html_mod.escape(_clean_text(prompt_text))
    return (
        '<button onclick="'
        "navigator.clipboard.writeText(document.getElementById('prompt-data').value)"
        ".then(function(){" + "window.open('" + doubao_url + "','_blank');"
        "var el=document.getElementById('status-msg');"
        "el.innerText='Done! Prompt copied. Doubao opened in new tab.';"
        "el.style.display='block';})"
        ".catch(function(){"
        "var el=document.getElementById('status-msg');"
        "el.innerText='Copy failed. Please copy the prompt manually.';"
        "el.style.display='block';});"
        '" style="background:linear-gradient(135deg,#4F8BF9,#FF6B6B);color:white;border:none;'
        'padding:12px 32px;border-radius:8px;cursor:pointer;font-size:16px;font-weight:bold;'
        'box-shadow:0 2px 8px rgba(0,0,0,0.15);width:100%">'
        'Copy Prompt + Open Doubao AI</button>'
        '<textarea id="prompt-data" style="position:absolute;left:-9999px">'
        + safe +
        '</textarea>'
        '<div id="status-msg" style="display:none;margin-top:8px;padding:8px 12px;'
        'background:#f0f9f0;border-radius:6px;color:#2e7d32;font-size:14px"></div>'
    )


@st.dialog("AI推文生成", width="large")
def show_ai_dialog(row_dict: dict):
    """Modal dialog for generating a Doubao AI social media post."""
    project_id = row_dict.get("id", 0)

    # Title + bookmark toggle
    tcol1, tcol2 = st.columns([5, 1])
    tcol1.markdown(f"### {row_dict.get('title', '')}")

    # Bookmark toggle
    engine = get_engine()
    current_bookmarks = _load_bookmarks(engine)
    is_bookmarked = project_id in current_bookmarks
    bookmark_label = "Unfavorite" if is_bookmarked else "Favorite"
    if tcol2.button(bookmark_label, use_container_width=True):
        _toggle_bookmark(engine, project_id)
        st.rerun()

    # Project info
    pcol1, pcol2 = st.columns(2)
    pcol1.write(f"**大学:** {row_dict.get('university', 'N/A')}")
    pcol1.write(f"**地区:** {row_dict.get('region_cn', 'N/A')} - {row_dict.get('country', 'N/A')}")
    pcol1.write(f"**资助类型:** {format_funding(row_dict.get('funding_type', ''))}")
    pcol2.write(f"**学科:** {row_dict.get('discipline', 'N/A')}")
    pcol2.write(f"**截止时间:** {row_dict.get('deadline', 'N/A')}")
    pcol2.write(f"**来源:** {row_dict.get('source', 'N/A')}")

    urgency = _parse_deadline_urgency(row_dict.get("deadline", ""))
    if urgency:
        if "Expired" in urgency:
            st.error(f"Deadline: {urgency}")
        elif "\U0001f534" in urgency:
            st.warning(f"Deadline: {urgency} - Apply ASAP!")
        elif "\U0001f7e1" in urgency:
            st.info(f"Deadline: {urgency}")

    if row_dict.get('url'):
        st.markdown(f"[>> 查看原始项目页面]({row_dict['url']})")

    st.markdown("---")

    default_prompt = _build_prompt(row_dict)
    prompt_text = st.text_area(
        "Edit prompt (editable before copying)",
        value=default_prompt,
        height=200,
    )

    btn_html = _doubao_button_html(prompt_text)
    st.components.v1.html(btn_html, height=80)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("🎓 PhD项目收集器")
st.sidebar.markdown("---")

# Manual scrape trigger
st.sidebar.caption("💡 建议每天采集1次即可，避免频繁请求")
if st.sidebar.button("🔄 立即采集", use_container_width=True):
    with st.spinner("正在采集数据，请稍候..."):
        collector = PhDCollector()
        stats = collector.run()
    st.sidebar.success(
        f"采集完成！\n\n"
        f"- 抓取: {stats['total_scraped']}\n"
        f"- 新增: {stats['new_saved']}\n"
        f"- 重复: {stats['duplicates']}\n"
        f"- 错误: {stats['errors']}"
    )
    st.rerun()

st.sidebar.markdown("---")

# Filters
st.sidebar.subheader("筛选条件")

engine = get_engine()
df = load_projects(engine)

def _needs_refresh(dataframe: pd.DataFrame, hours: int = 24) -> bool:
    """Check if the most recent collection is older than `hours` hours."""
    if dataframe.empty:
        return True
    try:
        latest = pd.to_datetime(dataframe["collected_at"]).max()
        if pd.isna(latest):
            return True
        age = datetime.now() - latest.replace(tzinfo=None)
        return age > timedelta(hours=hours)
    except Exception:
        return True

if df.empty or _needs_refresh(df):
    st.title("🎓 PhD项目收集器")
    if df.empty:
        st.info("数据库为空，正在自动采集数据，请稍候...")
    else:
        st.info("数据已超过24小时未更新，正在自动采集最新项目...")
    with st.spinner("正在从 FindAPhD / EURAXESS / ScholarshipDb / academics.de 采集PhD项目..."):
        collector = PhDCollector()
        stats = collector.run()
    st.success(
        f"自动采集完成！抓取 {stats['total_scraped']} 条，新增 {stats['new_saved']} 条。"
    )
    st.rerun()

# Region filter
all_regions = sorted(df["region_cn"].dropna().unique().tolist())
selected_regions = st.sidebar.multiselect("地区", all_regions, default=all_regions)

# Funding type filter
funding_options = ["全奖", "CSC", "Rolling", "岗位制", "未知"]
selected_funding = st.sidebar.multiselect("资助类型", funding_options, default=funding_options)

# Source filter
all_sources = sorted(df["source"].dropna().unique().tolist())
selected_sources = st.sidebar.multiselect("数据来源", all_sources, default=all_sources)

# Country filter
all_countries = sorted(df["country"].dropna().unique().tolist())
if all_countries:
    selected_countries = st.sidebar.multiselect("国家", all_countries, default=all_countries)
else:
    selected_countries = []

# Search
search_query = st.sidebar.text_input("🔍 关键词搜索", placeholder="输入标题/大学/导师关键词")

# Date range
date_range = st.sidebar.selectbox("时间范围", ["全部", "今天", "最近3天", "最近7天", "最近30天"])

# Bookmark filter
st.sidebar.markdown("---")
show_bookmarks_only = st.sidebar.toggle("⭐ 只看收藏", value=False)

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------
filtered = df.copy()

# Region
if selected_regions:
    filtered = filtered[filtered["region_cn"].isin(selected_regions)]

# Funding
if selected_funding:
    df_funding_cn = filtered["funding_type"].apply(format_funding)
    mask = df_funding_cn.apply(
        lambda x: any(f in x for f in selected_funding)
    )
    filtered = filtered[mask]

# Source
if selected_sources:
    filtered = filtered[filtered["source"].isin(selected_sources)]

# Country
if selected_countries:
    filtered = filtered[filtered["country"].isin(selected_countries)]

# Search
if search_query:
    q = search_query.lower()
    mask = (
        filtered["title"].str.lower().str.contains(q, na=False)
        | filtered["university"].str.lower().str.contains(q, na=False)
        | filtered["supervisor"].str.lower().str.contains(q, na=False)
        | filtered["discipline"].str.lower().str.contains(q, na=False)
        | filtered["description"].str.lower().str.contains(q, na=False)
    )
    filtered = filtered[mask]

# Date range
if date_range != "全部":
    days_map = {"今天": 0, "最近3天": 3, "最近7天": 7, "最近30天": 30}
    days = days_map.get(date_range, 0)
    if days == 0:
        cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    else:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filtered["collected_at"] = pd.to_datetime(filtered["collected_at"])
    filtered = filtered[filtered["collected_at"] >= cutoff]

# ---------------------------------------------------------------------------
# Apply bookmark filter
# ---------------------------------------------------------------------------
bookmarked_ids = _load_bookmarks(engine)
if show_bookmarks_only:
    filtered = filtered[filtered["id"].isin(bookmarked_ids)]

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
st.title("🎓 PhD项目收集器")

# Stats row
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("📊 总项目数", len(df))
col2.metric("🔍 筛选结果", len(filtered))

today_count = len(df[pd.to_datetime(df["collected_at"]).dt.date == datetime.now(timezone.utc).date()])
col3.metric("📅 今日新增", today_count)

source_count = df["source"].nunique()
col4.metric("🌐 数据源", source_count)
col5.metric("⭐ 已收藏", len(bookmarked_ids))

st.markdown("---")

# Charts row: region + funding + collection history
st.subheader("📊 数据概览")
col_chart1, col_chart2, col_chart3 = st.columns(3)

with col_chart1:
    st.caption("地区分布")
    region_counts = filtered["region_cn"].value_counts()
    st.bar_chart(region_counts)

with col_chart2:
    st.caption("资助类型")
    funding_display = filtered["funding_type"].apply(format_funding)
    funding_counts = funding_display.value_counts()
    st.bar_chart(funding_counts)

with col_chart3:
    st.caption("采集历史（每日新增）")
    history = df.copy()
    history["date"] = pd.to_datetime(history["collected_at"]).dt.date
    daily_counts = history.groupby("date").size().reset_index(name="count")
    daily_counts["date"] = pd.to_datetime(daily_counts["date"])
    daily_counts = daily_counts.set_index("date").sort_index()
    st.line_chart(daily_counts["count"])

st.markdown("---")

# Project table
st.subheader(f"📋 项目列表 ({len(filtered)} 条)")
st.caption("✅ 点击左侧复选框选中项目 → 弹出 AI 推文生成 + 收藏功能")

display_df = filtered[
    ["id", "title", "university", "supervisor", "region_cn", "country", "funding_type", "discipline", "deadline", "source", "url", "collected_at"]
].copy()

# Urgency column
display_df["紧迫度"] = display_df["deadline"].apply(_parse_deadline_urgency)

# Bookmark star column
display_df["收藏"] = display_df["id"].apply(lambda x: "\u2b50" if x in bookmarked_ids else "")

# Reorder: star + urgency first, then rest
display_df = display_df[[
    "收藏", "紧迫度", "title", "university", "supervisor", "region_cn", "country",
    "funding_type", "discipline", "deadline", "source", "url", "collected_at", "id"
]]

display_df.columns = [
    "⭐", "紧迫度", "项目标题", "大学", "导师", "地区", "国家", "资助类型", "学科", "截止时间", "来源", "链接", "收集时间", "_id"
]

display_df["资助类型"] = display_df["资助类型"].apply(format_funding)
display_df["收集时间"] = pd.to_datetime(display_df["收集时间"]).dt.strftime("%Y-%m-%d %H:%M")
display_df["链接"] = display_df["链接"].apply(lambda x: x if x else "")

# Hide _id column from display
event = st.dataframe(
    display_df,
    height=600,
    column_config={
        "链接": st.column_config.LinkColumn("链接", display_text="查看"),
        "_id": None,
    },
    on_select="rerun",
    selection_mode="single-row",
)

# ---------------------------------------------------------------------------
# Doubao AI - triggered by row selection -> opens dialog
# ---------------------------------------------------------------------------
selected_rows = event.selection.rows if event.selection else []

if selected_rows:
    row_idx = selected_rows[0]
    sel = filtered.iloc[row_idx]
    row_dict = {
        "id": int(sel.get("id", 0)),
        "title": str(sel.get("title", "")),
        "university": str(sel.get("university", "")),
        "country": str(sel.get("country", "")),
        "region_cn": str(sel.get("region_cn", "")),
        "discipline": str(sel.get("discipline", "")),
        "deadline": str(sel.get("deadline", "")),
        "funding_type": str(sel.get("funding_type", "")),
        "source": str(sel.get("source", "")),
        "url": str(sel.get("url", "")),
        "description": str(sel.get("description", "")),
    }
    show_ai_dialog(row_dict)

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
st.markdown("---")
col_exp1, col_exp2, _ = st.columns([1, 1, 3])

with col_exp1:
    csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 导出CSV",
        data=csv_data,
        file_name=f"phd_projects_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

with col_exp2:
    xlsx_buffer = io.BytesIO()
    display_df.to_excel(xlsx_buffer, index=False, engine="openpyxl")
    xlsx_buffer.seek(0)
    st.download_button(
        label="📥 导出Excel",
        data=xlsx_buffer.getvalue(),
        file_name=f"phd_projects_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    f"数据来源: FindAPhD, EURAXESS, ScholarshipDb, academics.de | "
    f"最后更新: {df['collected_at'].max() if not df.empty else 'N/A'} | "
    f"数据库总量: {len(df)} 条"
)
