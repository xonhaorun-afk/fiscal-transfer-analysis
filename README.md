# 中央—地方财政转移支付效果分析

[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![ECharts](https://img.shields.io/badge/ECharts-5.5-aa344d)](https://echarts.apache.org/)
[![scipy](https://img.shields.io/badge/scipy-统计检验-8c52ff)](https://scipy.org/)

基于国家统计局、财政部公开数据的综合定量研究——构建 2018–2024 年 31 省级行政区面板数据集，通过 **6 项核心指标 + 3 种统计检验** 评估中央转移支付的均等化效果。

> 🚀 **[在线演示（交互式仪表盘）](https://xonhaorun-afk.github.io/fiscal-transfer-analysis/)** — 打开后即可探索数据

## 核心发现

- **均等化方向正确**：低自给率省份人均转移支付是高自给率省份的 ~5 倍（`p < 0.001`）
- **地区差距依然严峻**：北京人均 GDP 约为甘肃的 4 倍，转移支付托底但无法根本改变经济格局
- **Pearson r = -0.97**（依赖度 vs 自给率），**Spearman ρ = -0.81**（依赖度 vs 人均 GDP）
- **ANOVA F = 62.10**：三类省份差异极显著，分类施策具有统计依据

## 快速开始

```bash
pip install -r requirements.txt   # 安装 Python 依赖
python main.py                     # 一键运行全流程
python -m pytest test_indicators.py -v  # 运行 16 个单元测试
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
├── config.py                # 公共配置
├── 01_数据采集.py            # 双模式数据采集（真实Excel + 在线备用）
├── 02_数据处理.py            # 数据清洗、6项指标、统计检验
├── 03_可视化.py              # geopandas 地图 + matplotlib 图表 + 仪表盘构建
├── dashboard_template.html  # ECharts 仪表盘模板
├── test_indicators.py       # 16 个单元测试
├── 数据/                    # 原始 Excel 数据（12 个文件）
└── output/                  # 输出（运行后生成）
    ├── dashboard.html       # 交互式仪表盘
    └── china_provinces.geojson
```

## 技术栈

| 层 | 工具 |
|---|------|
| 数据处理 | Python · pandas · numpy · scipy |
| 可视化 | matplotlib · geopandas · seaborn · ECharts |
| 统计检验 | Pearson r · Spearman ρ · 单因素 ANOVA · Bonferroni 校正 |
| 文档生成 | Node.js · docx · pptxgenjs |
| AI 协作 | Claude Code（全程辅助开发） |

## 交互式仪表盘

`output/dashboard.html` — 双击即用，无需服务器。5 个联动图表：

1. 省级分布地图（滚轮缩放，年份滑块，自动播放）
2. 财政自给率排名（三色分类）
3. 散点图（人均 GDP vs 人均转移支付）
4. 全国趋势（2018–2024 折线 + 面积图）
5. Pearson 相关系数热力图

同时部署于 GitHub Pages：[在线演示](https://xonhaorun-afk.github.io/fiscal-transfer-analysis/)

## 未来研究方向

当前工作聚焦于转移支付总量层面的描述性分析和统计检验。以下方向值得进一步深挖：

### 数据粒度细化
- **区分一般性 vs 专项转移支付**：两大类分配逻辑和效果截然不同。一般性转移支付侧重均等化，专项转移支付往往附带政策条件。拆分后可检验各自的实际效果
- **下沉至县级**：省级平均掩盖了省内差距。中国省以下财政体制差异巨大，县级数据能更精准地刻画转移支付的边际效应
- **对接公共服务产出**：引入教育（师生比）、医疗（千人床位数）、基建（路网密度）等产出指标，构建"投入 → 产出 → 效果"的完整评估链

### 分析方法升级
- **固定效应面板回归**：控制省份异质性后识别转移支付对地方公共服务和经济增长的因果效应
- **空间计量**：检验转移支付是否存在空间溢出——邻近省份获得的转移支付是否影响本省财政行为
- **分位数回归**：均等化效果在高依赖度省份和中等依赖度省份之间是否存在结构性差异

### 机制研究
- **财政激励效应（flypaper effect）**：转移支付是否抑制了地方自有税源的征收努力？即"越补越懒"是否存在
- **转移支付的动态响应**：地方财政支出对转移支付变化的短期和长期弹性是否对称

欢迎感兴趣的研究者在此基础上继续探索，或通过 Issue / PR 交流讨论。

## License

MIT — 自由使用、修改、分发。
