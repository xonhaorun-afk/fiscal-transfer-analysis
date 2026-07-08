# 中央—地方财政转移支付效果分析

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![ECharts](https://img.shields.io/badge/ECharts-5.5-aa344d)](https://echarts.apache.org/)
[![scipy](https://img.shields.io/badge/scipy-统计检验-8c52ff)](https://scipy.org/)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-blue)](.github/workflows/)

基于国家统计局、财政部公开数据的综合定量研究——构建 2018–2024 年 31 省级行政区面板数据集，通过 **6 项核心指标 + 5 种统计检验 + 4 种诊断检验 + 空间计量** 评估中央转移支付的均等化效果。

> 🚀 **[在线演示（交互式仪表盘）](https://xonhaorun-afk.github.io/fiscal-transfer-analysis/)** — 打开后即可探索数据

## 核心发现

- **均等化方向正确**：低自给率省份人均转移支付是高自给率省份的 ~5 倍（`p < 0.001`）
- **地区差距依然严峻**：北京人均 GDP 约为甘肃的 4 倍，转移支付托底但无法根本改变经济格局
- **Pearson r = -0.97**（依赖度 vs 自给率），**Spearman ρ = -0.81**（依赖度 vs 人均 GDP）
- **ANOVA F = 62.10**：三类省份差异极显著，分类施策具有统计依据
- **Moran's I = 0.42**：转移支付依赖度存在显著的空间聚集效应（p < 0.001）

## 快速开始

```bash
pip install -r requirements.txt   # 安装 Python 依赖
python main.py                     # 一键运行全流程
python -m pytest test_indicators.py -v  # 运行 29 个单元测试
```

可选：生成 Word 报告和 PPT

```bash
npm install            # 安装 Node.js 依赖（仅一次）
node generate_report.js
node generate_ppt.js
```

## 项目结构

```
├── main.py                  # 主入口，流程编排
├── config.py                # 公共配置（参数化阈值、年份范围）
├── 01_数据采集.py            # 三级回退数据采集（真实Excel > akshare在线 > 内置估算）
├── 02_数据处理.py            # 数据清洗、6项指标、统计检验、面板回归、诊断检验、空间计量
├── 03_可视化.py              # geopandas 地图 + matplotlib 图表 + 仪表盘构建
├── dashboard_template.html  # ECharts 仪表盘模板
├── test_indicators.py       # 29 个单元测试（配置、指标、回归、诊断）
├── .github/workflows/       # CI/CD 自动化（测试、构建、部署）
├── 数据/                    # 原始 Excel 数据（12 个文件）
└── output/                  # 输出（运行后生成）
    ├── dashboard.html       # 交互式仪表盘
    ├── panel_regression.csv # 面板固定效应回归结果
    ├── quantile_regression.csv # 分位数回归结果
    ├── vif_diagnostic.csv   # VIF 多重共线性检验
    ├── regression_diagnostic.csv # 诊断检验汇总
    ├── spatial_autocorrelation.csv # Moran's I 空间自相关
    └── china_provinces.geojson
```

## 技术栈

| 层 | 工具 |
|---|------|
| 数据处理 | Python · pandas · numpy · scipy · statsmodels · linearmodels |
| 数据采集 | akshare（国家统计局在线 API） · 本地 Excel 三级回退 |
| 可视化 | matplotlib · geopandas · seaborn · ECharts |
| 统计检验 | Pearson r · Spearman ρ · 单因素 ANOVA · Bonferroni · 面板固定效应回归 · 分位数回归 |
| 诊断检验 | VIF 多重共线性 · Breusch-Pagan 异方差 · 序列相关 · Moran's I 空间自相关 |
| 文档生成 | Node.js · docx · pptxgenjs |
| 工程化 | logging · 类型注解 · pytest 单元测试 · GitHub Actions CI/CD |

## 交互式仪表盘

`output/dashboard.html` — 双击即用，无需服务器。9 个联动图表：

1. 省级分布地图（滚轮缩放，年份滑块，自动播放）
2. 财政自给率排名（三色分类）
3. 散点图（人均 GDP vs 人均转移支付）
4. 全国趋势（2018–2024 折线 + 面积图）
5. Pearson 相关系数热力图
6. 依赖度分布时序箱线图
7. 三类省份依赖度时序对比
8. 面板固定效应回归系数森林图
9. 分位数回归系数变化图

同时部署于 GitHub Pages：[在线演示](https://xonhaorun-afk.github.io/fiscal-transfer-analysis/)

## 统计检验与诊断

项目实现了完整的统计检验链条：

### 推断性统计
| 检验方法 | 目的 | 结果 |
|---------|------|------|
| 面板固定效应回归 | 控制省份/时间异质性，识别净效应 | R²=0.72，ln人均GDP系数显著为负 |
| 分位数回归 | 检验不同依赖度水平上影响因素异质性 | 低依赖省份弹性更大 |

### 诊断检验
| 检验方法 | 目的 | 结果 |
|---------|------|------|
| VIF 多重共线性 | 检验解释变量相关性 | VIF=1.01，无共线性问题 |
| Breusch-Pagan 异方差 | 检验残差方差齐性 | p<0.05，存在异方差（已用聚类稳健标准误） |
| 一阶自相关 | 检验时间序列相关性 | 平均系数=0.72，存在正自相关 |
| Moran's I 空间自相关 | 检验空间聚集效应 | I=0.42, p<0.001，显著空间聚集 |

## CI/CD 自动化

每次 `git push` 自动触发：

1. **多版本 Python 测试**（3.10/3.11/3.12）
2. **pytest 单元测试**（29 个测试）
3. **全流程运行**（数据采集 → 处理 → 可视化）
4. **自动部署 GitHub Pages**（dashboard.html）

## 未来研究方向

当前工作聚焦于转移支付总量层面的描述性分析和统计检验。以下方向值得进一步深挖：

### 数据粒度细化
- **区分一般性 vs 专项转移支付**：两大类分配逻辑和效果截然不同。一般性转移支付侧重均等化，专项转移支付往往附带政策条件。拆分后可检验各自的实际效果
- **下沉至县级**：省级平均掩盖了省内差距。中国省以下财政体制差异巨大，县级数据能更精准地刻画转移支付的边际效应
- **对接公共服务产出**：引入教育（师生比）、医疗（千人床位数）、基建（路网密度）等产出指标，构建"投入 → 产出 → 效果"的完整评估链

### 分析方法升级
- **固定效应面板回归** ✅ 已实现：双向固定效应模型控制省份和时间异质性，聚类稳健标准误
- **空间计量** ✅ 已实现：Moran's I 检验证实转移支付依赖度存在显著空间聚集（I=0.42, p<0.001）
- **分位数回归** ✅ 已实现：在 25%~75% 分位点上检验均等化效果的异质性
- **空间滞后模型 (SLM)**：进一步量化空间溢出效应的大小

### 机制研究
- **财政激励效应（flypaper effect）**：转移支付是否抑制了地方自有税源的征收努力？即"越补越懒"是否存在
- **转移支付的动态响应**：地方财政支出对转移支付变化的短期和长期弹性是否对称

欢迎感兴趣的研究者在此基础上继续探索，或通过 Issue / PR 交流讨论。

## License

MIT — 自由使用、修改、分发。
