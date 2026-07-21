# 欧盟 / 法国 / 瑞典 电力市场政策追踪

每天自动抓取 CRE（法国）、Ei（瑞典）、ACER（欧盟）的最新新闻/政策动态，
存入 SQLite 数据库，用 Streamlit 展示成一个可搜索、可筛选的网页。

## 架构

```
GitHub Actions（每天定时）
        │
        ▼
python -m scraper.scrape   ← 抓取三个来源，写入 data/policy.db
        │
        ▼
  git commit + push        ← 自动提交更新后的数据库文件
        │
        ▼
Streamlit Community Cloud  ← 监听仓库变化，自动重新加载最新数据
        │
        ▼
      公开网页（谁都能打开的链接）
```

GitHub Actions 只负责"更新数据"，Streamlit Cloud 只负责"读数据、展示"，两者通过同一个GitHub仓库联动，你不需要手动做任何同步操作。

## 目录结构

```
eu-power-policy-tracker/
├── app.py                     # Streamlit 展示页面（这是网页的全部内容）
├── scraper/
│   ├── scrape.py              # 抓取入口：跑三个来源，写入SQLite
│   ├── db.py                  # SQLite 读写工具
│   ├── debug_fetch.py         # 调试工具：把某来源原始HTML存本地
│   └── sources/
│       ├── base.py            # 公共请求/解析函数
│       ├── cre_france.py      # 法国 CRE（已验证可用）
│       ├── ei_sweden.py       # 瑞典 Ei（已验证可用）
│       └── acer_eu.py         # 欧盟 ACER（选择器已核对，个别时候网站响应慢会超时）
├── data/policy.db             # SQLite数据库（脚本自动生成/更新，需要提交到git）
├── .streamlit/config.toml     # 深色主题配置
├── requirements.txt
└── .github/workflows/update.yml   # 每日定时自动抓取+提交
```

## 一、本地用 Anaconda 跑起来

```bash
conda create -n power-tracker python=3.11 -y
conda activate power-tracker

cd eu-power-policy-tracker
pip install -r requirements.txt

python -m scraper.scrape

streamlit run app.py
```

打开后你会看到：顶部是总条数统计，左侧可以按来源筛选、搜索关键词，主体是三栏并排的新闻列表。

## 二、如果某个来源抓不到数据

跟之前一样，用调试工具看原始HTML：
```bash
python -m scraper.debug_fetch acer
```
把 `data/debug/acer.html` 传给我，我帮你调整对应的 `scraper/sources/xxx.py`。

这几个抓取模块（cre_france.py / ei_sweden.py / acer_eu.py / base.py）跟之前静态页版本完全一样，不需要重新验证。

## 三、部署上线（免费，每天自动跑，所有人可访问）

### 1. 推送到 GitHub

```bash
git init
git add .
git commit -m "init: 迁移到 Streamlit + SQLite"
git branch -M main
git remote add origin https://github.com/你的用户名/power-policy-tracker.git
git push -u origin main
```

### 2. 手动跑一次抓取，先让数据库里有点数据再部署
（或者直接去 GitHub 仓库 Actions 标签页手动触发一次 workflow）

### 3. 部署到 Streamlit Community Cloud

1. 打开 https://share.streamlit.io，用 GitHub 账号登录（免费）
2. 点 "New app"，选择你刚推送的仓库、分支 main、入口文件填 app.py
3. 点部署，几分钟后会给你一个公开链接
4. 这个链接谁都能直接打开，不需要登录

### 4. 确认自动更新链路

- `.github/workflows/update.yml` 每天自动跑 `python -m scraper.scrape`，把新数据写进
  `data/policy.db` 并自动提交回仓库
- Streamlit Cloud 检测到仓库有新提交会自动重新加载，网页内容跟着更新
- 可以去 GitHub 仓库的 Actions 标签页手动点 "Run workflow" 立即测试

## 四、后续可以加的功能

- AI摘要/翻译/自动分类（需要接入付费的AI API，第一版先不加）
- 关键词自动打标签
- 更多数据源
- 邮件/微信每日推送
