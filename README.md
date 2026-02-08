# 🎓 PhD项目收集器

每日自动收集欧陆、澳洲、北美的PhD项目信息，支持筛选Rolling/全奖/CSC/岗位制类型。

**🌐 在线访问**: 部署在 Streamlit Cloud，任何设备浏览器均可访问。

## 功能

- **多源采集**: EURAXESS, ScholarshipDb（FindAPhD待接入）
- **三大地区**: 欧陆、澳洲、北美
- **智能分类**: 自动识别全奖/CSC/Rolling/岗位制
- **字段提取**: 国家、大学、学科、截止时间、导师
- **Web仪表盘**: 基于Streamlit的可视化界面
- **🤖 AI推文生成**: 一键生成小红书风格推文（集成豆包AI）
- **定时任务**: 每日自动采集（默认早8点）
- **数据导出**: 支持CSV/Excel导出
- **去重机制**: 基于URL自动去重，增量更新

## 在线使用（推荐）

直接在浏览器访问 Streamlit Cloud 部署的URL，首次访问会自动采集数据。

### 豆包AI推文生成

1. 在仪表盘底部「AI推文生成」区域选择一个PhD项目
2. 点击「📋 复制AI提示词」
3. 点击「🤖 打开豆包AI」
4. 在豆包对话框中粘贴提示词，即可生成小红书风格推文

## 本地运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动仪表盘

```bash
python main.py dashboard
```

浏览器访问 http://localhost:8501

### 3. 手动采集

```bash
python main.py scrape
```

### 4. 启动定时任务

```bash
python main.py scheduler
```

## 项目结构

```
phd/
├── main.py              # 主入口
├── config.py            # 全局配置
├── models.py            # 数据库模型
├── collector.py         # 采集引擎
├── scheduler.py         # 定时调度
├── dashboard.py         # Streamlit仪表盘
├── requirements.txt     # 依赖
├── packages.txt         # 系统依赖（Streamlit Cloud用）
├── data/                # SQLite数据库存储
└── scrapers/
    ├── __init__.py
    ├── base.py          # 爬虫基类
    ├── findaphd.py      # FindAPhD爬虫（暂未启用）
    ├── euraxess.py      # EURAXESS爬虫
    └── scholarshipdb.py # ScholarshipDb爬虫
```

## 配置

编辑 `config.py` 可调整：

- `SCRAPE_HOUR` / `SCRAPE_MINUTE`: 每日采集时间
- `MAX_PAGES`: 每个数据源的最大翻页数
- `REQUEST_DELAY`: 请求间隔（秒）
- `FUNDING_KEYWORDS`: 资助类型关键词

## 数据源

| 数据源 | 状态 | 覆盖地区 | 提取字段 | 说明 |
|--------|------|---------|----------|------|
| EURAXESS | ✅ 已启用 | 欧洲 | 国家、大学、学科、截止时间 | 欧盟官方研究人员门户 |
| ScholarshipDb | ✅ 已启用 | 全球 | 大学、地区、学科（关键词推断） | 奖学金数据库 |
| FindAPhD | ⏸️ 待接入 | 全球 | - | Cloudflare防护，待后续接入 |

## 注意事项

- **采集频率**: 建议每天采集1次即可，频繁采集无意义且可能触发网站限制
- **首次访问**: Streamlit Cloud部署版首次访问会自动采集，无需手动操作
- **本地运行**: 首次运行请点击仪表盘中的「立即采集」按钮
- **数据源稳定性**: ScholarshipDb偶尔返回500/520错误属于正常现象（服务器不稳定），不影响整体使用
- **网站结构变化**: 如采集失败请检查日志 `phd_collector.log`
