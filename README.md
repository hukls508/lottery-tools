# 彩票选号娱乐工具（自动更新版）

双色球和大乐透选号工具，支持 GitHub Actions 每期自动更新开奖数据。

## 功能

- **双色球**：红球1-33选6，蓝球1-16选1
- **大乐透**：前区1-35选5，后区1-12选2
- 历史开奖数据展示（近5/10/30天切换）
- 号码频次统计 & 冷热分析
- 手动选号 + 一键随机生成多组
- 每组号码附带组合逻辑说明
- 手机端适配，微信内可直接打开

## 项目结构

```
lottery-tools/
├── ssq.html                  # 双色球页面
├── dlt.html                  # 大乐透页面
├── data/
│   ├── ssq.json              # 双色球历史数据
│   └── dlt.json              # 大乐透历史数据
├── scripts/
│   └── fetch.py              # 自动抓取脚本
├── .github/workflows/
│   └── update.yml            # GitHub Actions 自动更新配置
└── README.md
```

## 部署步骤

### 1. 创建 GitHub 仓库

在 GitHub 上新建一个仓库（如 `lottery-tools`），把本项目所有文件推送到仓库。

### 2. 开启 GitHub Pages

- 进入仓库 Settings → Pages
- Source 选择 `Deploy from a branch`
- Branch 选择 `main` / `root`，保存
- 等待几分钟后，会得到一个访问地址，如：
  `https://你的用户名.github.io/lottery-tools/ssq.html`

### 3. 确认 Actions 权限

- 进入仓库 Settings → Actions → General
- 找到 "Workflow permissions"，选择 **Read and write permissions**
- 保存（这样 Actions 才能自动提交更新的数据）

### 4. 手动触发一次测试

- 进入仓库 Actions → 选择 "自动更新开奖数据"
- 点击 "Run workflow" 手动运行一次
- 确认运行成功，数据文件被更新

## 自动更新机制

- **运行时间**：每天北京时间 22:00（UTC 14:00）自动运行
- **数据源**：中彩网 zhcw.com
- **更新逻辑**：抓取最新开奖数据，与本地对比，只追加新期号
- **提交方式**：有新数据时自动 commit 并 push 到仓库
- **页面生效**：GitHub Pages 会在几分钟内自动部署更新

双色球开奖时间：每周二、四、日 21:15
大乐透开奖时间：每周一、三、六 21:25

## 本地测试抓取脚本

```bash
python3 scripts/fetch.py
```

## 注意事项

- 本工具仅供娱乐参考，彩票开奖为独立随机事件
- 抓取依赖中彩网页面结构，如网站改版可能需要调整解析逻辑
- GitHub Pages 为静态托管，页面通过 fetch 读取同目录下的 JSON 数据
