"""Streamlit dashboard for PhD Project Collector."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import html as html_mod
import urllib.parse

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from models import PhDProject, init_db
from config import DB_URL
from collector import PhDCollector

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

if df.empty:
    st.title("🎓 PhD项目收集器")
    st.info("数据库为空，正在自动采集数据，请稍候...")
    with st.spinner("首次访问，正在从 EURAXESS / ScholarshipDb 采集PhD项目..."):
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
# Main content
# ---------------------------------------------------------------------------
st.title("🎓 PhD项目收集器")

# Stats row
col1, col2, col3, col4 = st.columns(4)
col1.metric("📊 总项目数", len(df))
col2.metric("🔍 筛选结果", len(filtered))

today_count = len(df[pd.to_datetime(df["collected_at"]).dt.date == datetime.now(timezone.utc).date()])
col3.metric("📅 今日新增", today_count)

source_count = df["source"].nunique()
col4.metric("🌐 数据源", source_count)

st.markdown("---")

# Region distribution chart
st.subheader("📊 地区分布")
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    region_counts = filtered["region_cn"].value_counts()
    st.bar_chart(region_counts)

with col_chart2:
    funding_display = filtered["funding_type"].apply(format_funding)
    funding_counts = funding_display.value_counts()
    st.bar_chart(funding_counts)

st.markdown("---")

# Project table
st.subheader(f"📋 项目列表 ({len(filtered)} 条)")

display_df = filtered[
    ["title", "university", "supervisor", "region_cn", "country", "funding_type", "discipline", "deadline", "source", "url", "collected_at"]
].copy()

display_df.columns = [
    "项目标题", "大学", "导师", "地区", "国家", "资助类型", "学科", "截止时间", "来源", "链接", "收集时间"
]

display_df["资助类型"] = display_df["资助类型"].apply(format_funding)
display_df["收集时间"] = pd.to_datetime(display_df["收集时间"]).dt.strftime("%Y-%m-%d %H:%M")

# Make URL clickable
display_df["链接"] = display_df["链接"].apply(lambda x: x if x else "")

event = st.dataframe(
    display_df,
    height=600,
    column_config={
        "链接": st.column_config.LinkColumn("链接", display_text="查看"),
        "项目标题": st.column_config.TextColumn("项目标题"),
    },
    on_select="rerun",
    selection_mode="single-row",
)

# ---------------------------------------------------------------------------
# Doubao AI - triggered by row selection
# ---------------------------------------------------------------------------
selected_rows = event.selection.rows if event.selection else []

if selected_rows:
    row_idx = selected_rows[0]
    sel = filtered.iloc[row_idx]

    st.markdown("---")
    st.subheader(f"🤖 为「{sel.get('title', '')[:40]}...」生成推文")

    # Project summary
    pcol1, pcol2, pcol3 = st.columns(3)
    pcol1.write(f"**大学:** {sel.get('university', 'N/A')}")
    pcol1.write(f"**地区:** {sel.get('region_cn', 'N/A')} · {sel.get('country', 'N/A')}")
    pcol2.write(f"**学科:** {sel.get('discipline', 'N/A')}")
    pcol2.write(f"**截止时间:** {sel.get('deadline', 'N/A')}")
    pcol3.write(f"**资助类型:** {format_funding(sel.get('funding_type', ''))}")
    pcol3.write(f"**来源:** {sel.get('source', 'N/A')}")

    project_url = sel.get("url", "")
    default_prompt = (
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
        f"标题格式：🇸🇪[国旗] + 大学名 + 博士项目招生更新！\n"
        f"内容包括：学校亮点、资助待遇、热门项目一览、申请贴士、适合人群\n"
        f"语气活泼、信息丰富，适合小红书发布。"
    )

    # Editable prompt
    prompt_text = st.text_area(
        "✏️ 编辑提示词（可自由修改后再复制）",
        value=default_prompt,
        height=200,
        key=f"prompt_{row_idx}",
    )

    # Single combined button: copy prompt + open Doubao
    doubao_url = "https://www.doubao.com/chat/"
    safe_prompt = html_mod.escape(prompt_text)
    combined_js = f"""
    <button onclick="
        navigator.clipboard.writeText(document.getElementById('prompt-data').value)
            .then(function() {{
                window.open('{doubao_url}', '_blank');
                var el = document.getElementById('status-msg');
                el.innerText = '\u2705 \u63d0\u793a\u8bcd\u5df2\u590d\u5236\uff01\u8c46\u5305AI\u5df2\u5728\u65b0\u6807\u7b7e\u9875\u6253\u5f00\uff0c\u8bf7\u7c98\u8d34\u63d0\u793a\u8bcd';
                el.style.display = 'block';
            }})
            .catch(function() {{
                var el = document.getElementById('status-msg');
                el.innerText = '\u274c \u590d\u5236\u5931\u8d25\uff0c\u8bf7\u624b\u52a8\u590d\u5236\u4e0b\u65b9\u63d0\u793a\u8bcd';
                el.style.display = 'block';
            }});
    " style="background:linear-gradient(135deg,#4F8BF9,#FF6B6B);color:white;border:none;
             padding:12px 32px;border-radius:8px;cursor:pointer;font-size:16px;font-weight:bold;
             box-shadow:0 2px 8px rgba(0,0,0,0.15);transition:transform 0.1s"
    onmouseover="this.style.transform='scale(1.02)'"
    onmouseout="this.style.transform='scale(1)'">
    \ud83d\udccb\ud83e\udd16 \u590d\u5236\u63d0\u793a\u8bcd\u5e76\u6253\u5f00\u8c46\u5305AI
    </button>
    <textarea id="prompt-data" style="position:absolute;left:-9999px">{safe_prompt}</textarea>
    <div id="status-msg" style="display:none;margin-top:8px;padding:8px 12px;
         background:#f0f9f0;border-radius:6px;color:#2e7d32;font-size:14px"></div>
    """
    st.components.v1.html(combined_js, height=90)
else:
    st.info("👆 点击表格中的任意一行，即可生成AI推文")

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
    st.download_button(
        label="📥 导出Excel",
        data=csv_data,
        file_name=f"phd_projects_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.ms-excel",
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    f"数据来源: EURAXESS, ScholarshipDb | "
    f"最后更新: {df['collected_at'].max() if not df.empty else 'N/A'} | "
    f"数据库总量: {len(df)} 条"
)
