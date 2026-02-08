# 🎓 PhD项目收集器

每日自动收集欧陆、澳洲、北美的PhD项目信息，支持筛选Rolling/全奖/CSC/岗位制类型。

## 功能

- **多源采集**: FindAPhD, EURAXESS, ScholarshipDb
- **三大地区**: 欧陆、澳洲、北美
- **智能分类**: 自动识别全奖/CSC/Rolling/岗位制
- **Web仪表盘**: 基于Streamlit的可视化界面
- **定时任务**: 每日自动采集（默认早8点）
- **数据导出**: 支持CSV/Excel导出
- **去重机制**: 基于URL自动去重，增量更新

## 快速开始

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
├── data/                # SQLite数据库存储
└── scrapers/
    ├── __init__.py
    ├── base.py          # 爬虫基类
    ├── findaphd.py      # FindAPhD爬虫
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

| 数据源 | 覆盖地区 | 说明 |
|--------|---------|------|
| FindAPhD | 全球 | 最大的PhD项目数据库 |
| EURAXESS | 欧洲 | 欧盟官方研究人员门户 |
| ScholarshipDb | 全球 | 奖学金数据库 |

## 注意事项

- 首次运行请先点击仪表盘中的「立即采集」按钮
- 爬虫会自动控制请求频率，避免对目标网站造成压力
- 网站结构可能变化，如采集失败请检查日志 `phd_collector.log`
