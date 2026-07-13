# 研究方法模板项目

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"></a>
  <a href="https://echarts.apache.org/"><img src="https://img.shields.io/badge/ECharts-5.5-aa344d.svg" alt="ECharts"></a>
  <a href="https://scipy.org/"><img src="https://img.shields.io/badge/scipy-统计检验-8c52ff.svg" alt="scipy"></a>
</p>

<p align="center">
  <strong>可复用的面板数据研究全流程框架</strong>
</p>

---

## 📖 这是什么？

这是一个从「中央—地方财政转移支付效果分析」项目中提炼出来的**通用研究方法模板**，将完整的数据分析流程标准化，可快速复用到各类面板数据研究中。

**核心方法论：**
- 三级回退数据采集策略
- 面板数据指标计算体系
- 完整的统计检验与诊断
- 多维可视化 + 交互式仪表盘
- 自动化报告与PPT生成
- 工程化测试与CI/CD

---

## 🎯 适用场景

- 区域经济差异分析
- 产业发展评估
- 公共政策效果评价
- 社会事业均衡性研究
- 资源配置效率分析
- 文旅、教育、医疗等各领域

---

## 🚀 快速开始

### 1. 阅读复用指南
👉 [USAGE.md](USAGE.md) — 详细的5步复用教程 + 实战示例

### 2. 修改配置
编辑 [config.py](config.py)，设置你的研究主题、区域、指标体系：

```python
PROJECT_NAME = "你的研究项目名称"
PROJECT_SUBTITLE = "研究副标题"
REGIONS = [...]  # 研究区域列表
YEAR_START = 2018
YEAR_END = 2024
```

### 3. 准备数据
将Excel数据放入 `data/` 目录。

### 4. 运行全流程
```bash
pip install -r requirements.txt
python main.py
```

可选：生成Word报告和PPT
```bash
npm install
node generate_report.js
node generate_ppt.js
```

---

## 📁 项目结构

```
├── main.py                  # 主入口，流程编排
├── config.py                # ⭐ 所有研究主题配置集中在此
├── 01_数据采集.py            # 三级回退数据采集
├── 02_数据处理.py            # 指标计算 + 统计检验 + 回归分析
├── 03_可视化.py              # 地图 + 图表 + 仪表盘构建
├── dashboard_template.html  # ECharts 仪表盘模板（9图联动）
├── test_indicators.py       # 单元测试
├── generate_report.js       # Word 报告自动生成
├── generate_ppt.js          # PPT 演示文稿自动生成
├── .github/workflows/ci.yml # CI/CD 自动化
├── data/                    # 原始数据（Excel）
├── output/                  # 输出结果（运行后生成）
├── USAGE.md                 # 📖 详细复用指南
└── README.md                # 本文件
```

---

## 🛠 技术栈

| 层 | 工具 |
|---|------|
| **数据处理** | Python · pandas · numpy · scipy · statsmodels · linearmodels |
| **数据采集** | akshare · 本地Excel · 三级回退策略 |
| **可视化** | matplotlib · geopandas · seaborn · ECharts |
| **统计检验** | Pearson r · Spearman ρ · ANOVA · 面板固定效应回归 · 分位数回归 |
| **诊断检验** | VIF · Breusch-Pagan · 序列相关 · Moran's I |
| **文档生成** | Node.js · docx · pptxgenjs |
| **工程化** | logging · pytest · GitHub Actions |

---

## 📊 输出物

运行 `python main.py` 后，`output/` 目录包含：

- 📈 **18张统计图表** + 5张区域分布地图
- 🖥 **交互式仪表盘**（dashboard.html，9个联动图表）
- 📄 **完整研究报告**（项目报告.docx）
- 🎯 **PPT演示文稿**（课堂演示.pptx）
- 📊 **统计结果数据**（回归、诊断、空间分析等CSV）

---

## 📖 详细文档

- **[USAGE.md](USAGE.md)** — 完整复用指南，含：
  - 5步快速上手教程
  - 各模块改造要点详解
  - 「转移支付 → 文旅分析」实战示例
  - 常见问题解答

---

## 📝 原项目参考

本模板提炼自「中央—地方财政转移支付效果分析」项目，原始项目包含完整的省级财政数据和分析结果，可作为参考范例。

---

## 📄 License

MIT — 自由使用、修改、分发。
