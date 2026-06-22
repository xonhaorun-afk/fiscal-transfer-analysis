const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const OUT_DIR = path.join(__dirname, "output");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "辛浩然";
pres.title = "中央—地方财政转移支付效果分析";

const C = {
  navy: "1A3C5E", darkBlue: "1F4E79", blue: "2E75B6",
  lightBlue: "D5E8F0", accent: "C0392B", white: "FFFFFF",
  offWhite: "F5F7FA", gray: "64748B", dark: "1E293B",
  green: "27AE60", orange: "E67E22", red: "C0392B",
};

function imgBase64(filename) {
  const p = path.join(OUT_DIR, filename);
  if (fs.existsSync(p)) return "image/png;base64," + fs.readFileSync(p).toString("base64");
  return null;
}

const imgDepend = imgBase64("地图_转移支付依赖度.png");
const imgFiscal = imgBase64("地图_财政自给率.png");
const imgTimeline = imgBase64("地图_转移支付依赖度_时序.png");
const imgDashboard = imgBase64("仪表盘_综合.png");
const imgScatter = imgBase64("统计图_转移支付vs人均GDP.png");
const imgTrend = imgBase64("统计图_全国趋势.png");
const imgRanking = imgBase64("统计图_财政自给率排名.png");
const imgCategory = imgBase64("统计图_三类省份对比.png");
const imgHeatmap = imgBase64("统计图_相关性热力图.png");

// ===== 工具函数 =====
function sectionTitle(s, text) {
  s.addText(text, { x: 0.5, y: 0.2, w: 9, h: 0.55, fontSize: 24, fontFace: "Microsoft YaHei", color: C.navy, bold: true });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 0.75, w: 1.0, h: 0.03, fill: { color: C.blue } });
}

function statBox(s, x, y, w, number, label, color) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 1.1, fill: { color: C.offWhite } });
  s.addText(number, { x, y: y + 0.05, w, h: 0.55, fontSize: 28, fontFace: "Microsoft YaHei", color, bold: true, align: "center", valign: "middle" });
  s.addText(label, { x, y: y + 0.6, w, h: 0.4, fontSize: 11, fontFace: "Microsoft YaHei", color: C.gray, align: "center", valign: "top" });
}

function aiBar(s, x, y, w, text) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h: 0.26, fill: { color: C.lightBlue } });
  s.addText("AI协作：" + text, { x: x + 0.06, y, w: w - 0.12, h: 0.26, fontSize: 7.5, fontFace: "Microsoft YaHei", color: C.darkBlue, valign: "middle" });
}

// ================================================================
// Slide 1: 封面
// ================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  s.addText("中央—地方财政转移支付\n效果分析", {
    x: 0.8, y: 1.0, w: 8.4, h: 2.0, fontSize: 40, fontFace: "Microsoft YaHei",
    color: C.white, bold: true, lineSpacingMultiple: 1.3,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 3.1, w: 1.5, h: 0.05, fill: { color: C.accent } });
  s.addText("基于多源部委数据的综合定量研究", {
    x: 0.8, y: 3.3, w: 8, h: 0.6, fontSize: 18, fontFace: "Microsoft YaHei", color: C.lightBlue,
  });
  s.addText("人工智能与计算思维 · 2026年春季学期大作业\n单人完成  |  Python + ECharts  |  Claude Code 协作开发", {
    x: 0.8, y: 4.2, w: 8, h: 0.8, fontSize: 13, fontFace: "Microsoft YaHei", color: C.gray, lineSpacingMultiple: 1.5,
  });
}

// ================================================================
// Slide 2: 问题提出
// ================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  sectionTitle(s, "问题提出：中央转移支付的分配效果");

  // 核心数据
  statBox(s, 0.5, 1.1, 2.8, "约10万亿", "2024年转移支付总额", C.navy);
  statBox(s, 3.5, 1.1, 2.8, "约47%", "占地方财政支出比重", C.accent);
  statBox(s, 6.5, 1.1, 2.8, "31省 × 7年", "面板数据规模", C.blue);

  // 研究问题
  s.addText("核心研究问题", { x: 0.5, y: 2.6, w: 8, h: 0.4, fontSize: 16, fontFace: "Microsoft YaHei", color: C.dark, bold: true });
  s.addText([
    { text: "1. 中央转移支付是否有效缩小了地区间财力差距？", options: { bullet: true, breakLine: true, fontSize: 14 } },
    { text: "2. 哪些省份对中央转移支付的依赖程度最高？背后的经济与财政因素是什么？", options: { bullet: true, breakLine: true, fontSize: 14 } },
    { text: "3. 转移支付的分配是否与经济发展水平、人口结构等指标匹配？", options: { bullet: true, fontSize: 14 } },
  ], { x: 0.5, y: 3.0, w: 8.8, h: 1.4, fontFace: "Microsoft YaHei", color: C.dark });

  aiBar(s, 0.5, 4.8, 9, "从8个候选选题中评估匹配度，结合政府管理专业背景推荐转移支付方向");
}

// ================================================================
// Slide 3: 研究方法
// ================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  sectionTitle(s, "研究方法：数据、指标与分析框架");

  // 左侧：数据来源
  s.addText("数据来源", { x: 0.5, y: 1.05, w: 4, h: 0.3, fontSize: 14, fontFace: "Microsoft YaHei", color: C.navy, bold: true });
  const srcs = [
    { dept: "国家统计局", data: "GDP、常住人口", platform: "EPS数据平台" },
    { dept: "财政部", data: "财政收入、财政支出", platform: "EPS数据平台" },
    { dept: "财政部预算司", data: "中央转移支付", platform: "决算表手工整理" },
  ];
  srcs.forEach((src, i) => {
    const sy = 1.45 + i * 0.65;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: sy, w: 4.3, h: 0.55, fill: { color: C.offWhite } });
    s.addText(src.dept, { x: 0.6, y: sy + 0.02, w: 1.6, h: 0.5, fontSize: 12, fontFace: "Microsoft YaHei", color: C.darkBlue, bold: true, valign: "middle" });
    s.addText(src.data + "\n" + src.platform, { x: 2.2, y: sy + 0.02, w: 2.5, h: 0.5, fontSize: 10, fontFace: "Microsoft YaHei", color: C.gray, valign: "middle" });
  });

  // 右侧：指标体系
  s.addText("六项核心指标", { x: 5.2, y: 1.05, w: 4.5, h: 0.3, fontSize: 14, fontFace: "Microsoft YaHei", color: C.navy, bold: true });
  const metrics = [
    { name: "转移支付依赖度", formula: "转移支付 ÷ 财政支出" },
    { name: "人均转移支付", formula: "转移支付 ÷ 常住人口" },
    { name: "财政自给率", formula: "财政收入 ÷ 财政支出" },
    { name: "人均GDP", formula: "GDP ÷ 人口（经济基准）" },
    { name: "经济匹配指数", formula: "人均转移支付 ÷ 人均GDP" },
    { name: "增速差", formula: "转移支付增速 − GDP增速" },
  ];
  metrics.forEach((m, i) => {
    const my = 1.45 + i * 0.46;
    s.addText(m.name, { x: 5.3, y: my, w: 2.2, h: 0.38, fontSize: 10, fontFace: "Microsoft YaHei", color: C.dark, bold: true, valign: "middle" });
    s.addText(m.formula, { x: 7.5, y: my, w: 2.2, h: 0.38, fontSize: 9, fontFace: "Consolas", color: C.gray, valign: "middle" });
  });

  // 底部：分析框架
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.3, w: 9, h: 0.4, fill: { color: C.lightBlue } });
  s.addText("分析框架：描述性统计 → 分组对比（三类省份）→ 统计检验（Pearson r / Spearman ρ / ANOVA）→ 政策启示", {
    x: 0.6, y: 4.3, w: 8.8, h: 0.4, fontSize: 11, fontFace: "Microsoft YaHei", color: C.darkBlue, valign: "middle",
  });

  aiBar(s, 0.5, 4.9, 9, "输出指标体系设计 + 四阶段流水线架构（采集→处理→可视化→报告）");
}

// ================================================================
// Slide 4: 结果① — 依赖度地区分布
// ================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  sectionTitle(s, "结果①：转移支付依赖度的地区分布");

  if (imgDepend) s.addImage({ data: imgDepend, x: 0.1, y: 0.95, w: 5.0, h: 3.3 });
  if (imgFiscal) s.addImage({ data: imgFiscal, x: 5.1, y: 0.95, w: 4.7, h: 3.3 });

  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.45, w: 4.5, h: 0.45, fill: { color: C.red } });
  s.addText("西藏依赖度 88.0%  vs  上海 9.6%  ·  极差 78.4 个百分点", {
    x: 0.5, y: 4.45, w: 4.5, h: 0.45, fontSize: 12, fontFace: "Microsoft YaHei", color: C.white, bold: true, align: "center", valign: "middle",
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 4.45, w: 4.5, h: 0.45, fill: { color: C.darkBlue } });
  s.addText("整体呈东低西高格局  高依赖省份集中在西部", {
    x: 5.2, y: 4.45, w: 4.5, h: 0.45, fontSize: 12, fontFace: "Microsoft YaHei", color: C.white, bold: true, align: "center", valign: "middle",
  });

  aiBar(s, 0.5, 5.1, 9, "geopandas choropleth 地图 + 红蓝双色时序变化量（较上年差额，百分点）");
}

// ================================================================
// Slide 5: 结果② — 财政自给率与经济发展
// ================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  sectionTitle(s, "结果②：财政自给率与转移支付-经济关系");

  if (imgRanking) s.addImage({ data: imgRanking, x: 0.1, y: 0.9, w: 4.6, h: 4.0 });
  if (imgScatter) s.addImage({ data: imgScatter, x: 4.9, y: 0.9, w: 5.1, h: 4.0 });

  s.addText("左：31省财政自给率排名。红/橙/蓝三色对应低/中/高三类自给率。上海84.8% → 西藏9.5%，差距悬殊", {
    x: 0.5, y: 5.0, w: 9, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei", color: C.gray,
  });

  aiBar(s, 0.5, 5.35, 9, "geopandas + matplotlib 生成，气泡大小=人口量，颜色=自给率等级");
}

// ================================================================
// Slide 6: 结果③ — 三类省份对比
// ================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  sectionTitle(s, "结果③：三类财政自给率省份的关键指标");

  const cats = [
    { label: "高自给率 ≥60%", count: "5省", examples: "上海、北京、广东\n浙江、江苏", color: C.green, dep: "13.9%", per: "3,672元", gdp: "170,057元" },
    { label: "中自给率 35-60%", count: "16省", examples: "山东、福建、山西\n内蒙古、辽宁等", color: C.orange, dep: "44.2%", per: "7,729元", gdp: "90,195元" },
    { label: "低自给率 <35%", count: "10省", examples: "西藏、甘肃、青海\n宁夏、黑龙江等", color: C.red, dep: "68.0%", per: "19,916元", gdp: "64,863元" },
  ];
  cats.forEach((cat, i) => {
    const cx = 0.4 + i * 3.15;
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.05, w: 2.95, h: 3.1, fill: { color: C.offWhite } });
    s.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.05, w: 2.95, h: 0.06, fill: { color: cat.color } });
    s.addText(cat.label, { x: cx + 0.12, y: 1.15, w: 2.7, h: 0.32, fontSize: 13, fontFace: "Microsoft YaHei", color: cat.color, bold: true });
    s.addText(cat.count, { x: cx + 0.12, y: 1.45, w: 2.7, h: 0.28, fontSize: 22, fontFace: "Microsoft YaHei", color: C.dark, bold: true });
    s.addText("依赖度: " + cat.dep + "\n人均转移支付: " + cat.per + "\n人均GDP: " + cat.gdp, {
      x: cx + 0.12, y: 1.8, w: 2.7, h: 1.4, fontSize: 11, fontFace: "Microsoft YaHei", color: C.dark, lineSpacingMultiple: 1.6,
    });
    s.addText(cat.examples, { x: cx + 0.12, y: 3.4, w: 2.7, h: 0.6, fontSize: 9, fontFace: "Microsoft YaHei", color: C.gray });
  });

  s.addText("低自给率省份人均转移支付是高自给率的5.4倍 → 转移支付向财力薄弱地区倾斜。但人均GDP差距（17.0万 vs 6.5万）同样显著", {
    x: 0.5, y: 4.4, w: 9, h: 0.7, fontSize: 12, fontFace: "Microsoft YaHei", color: C.gray, italic: true,
  });

  aiBar(s, 0.5, 5.2, 9, "AI自动计算三类均值并对齐结论 → 人补充政策解读：专项与一般性转移支付分配逻辑不同");
}

// ================================================================
// Slide 7: 结果④ — 趋势与时序
// ================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  sectionTitle(s, "结果④：全国趋势与逐年变化");

  if (imgTrend) s.addImage({ data: imgTrend, x: 0.1, y: 0.9, w: 4.8, h: 3.5 });
  if (imgTimeline) s.addImage({ data: imgTimeline, x: 5.1, y: 0.9, w: 4.7, h: 3.5 });

  s.addText([
    { text: "左图：", options: { bold: true, fontSize: 11 } },
    { text: "全国平均依赖度从37.4%(2018)升至47.0%(2024)，增长约10个百分点。转移支付总额从6万亿增至10万亿，年均增速约9%。", options: { fontSize: 11 } },
  ], { x: 0.5, y: 4.6, w: 4.6, h: 0.7, fontFace: "Microsoft YaHei", color: C.gray });
  s.addText([
    { text: "右图：", options: { bold: true, fontSize: 11 } },
    { text: "逐年变化量 = 当年依赖度 − 上年依赖度。红色=加深依赖，蓝色=减轻依赖。多数中西部省份波动在±5个百分点之间。", options: { fontSize: 11 } },
  ], { x: 5.2, y: 4.6, w: 4.5, h: 0.7, fontFace: "Microsoft YaHei", color: C.gray });

  aiBar(s, 0.5, 5.4, 9, "matplotlib折线+面积图 / geopandas 6子图红蓝时序变化量（设计由绝对值改为较上年差额）");
}

// ================================================================
// Slide 8: 结果⑤ — 统计检验
// ================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  sectionTitle(s, "结果⑤：统计检验 — 显著性验证");

  if (imgHeatmap) s.addImage({ data: imgHeatmap, x: 0.1, y: 1.0, w: 4.6, h: 3.8 });

  // 右侧：统计结果
  const stats = [
    { label: "Pearson r", value: "依赖度 vs 自给率: r = -0.9749", detail: "近乎完全负相关" },
    { label: "Pearson r", value: "依赖度 vs 人均GDP: r = -0.7751", detail: "强负相关" },
    { label: "Spearman ρ", value: "ρ = -0.8129, p < 0.001", detail: "单调关系极显著" },
    { label: "单因素 ANOVA", value: "F = 62.10, p < 0.001", detail: "三类省份差异极显著" },
    { label: "事后比较", value: "高/中/低 两两比较 p < 0.001", detail: "Bonferroni校正全部显著" },
  ];
  stats.forEach((st, i) => {
    const sy = 1.1 + i * 0.72;
    s.addShape(pres.shapes.RECTANGLE, { x: 5.0, y: sy, w: 4.7, h: 0.62, fill: { color: C.offWhite } });
    s.addShape(pres.shapes.RECTANGLE, { x: 5.0, y: sy, w: 0.05, h: 0.62, fill: { color: C.blue } });
    s.addText(st.value, { x: 5.15, y: sy + 0.02, w: 4.4, h: 0.35, fontSize: 11, fontFace: "Microsoft YaHei", color: C.dark, bold: true, valign: "bottom" });
    s.addText(st.detail, { x: 5.15, y: sy + 0.32, w: 4.4, h: 0.28, fontSize: 9, fontFace: "Microsoft YaHei", color: C.gray, valign: "top" });
  });

  aiBar(s, 0.5, 5.3, 9, "scipy Pearson/Spearman/ANOVA → 为描述性发现提供统计显著性支撑 → 增强结论可信度");
}

// ================================================================
// Slide 9: 结论与政策启示
// ================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  sectionTitle(s, "结论与政策启示");

  // 左侧：核心结论
  s.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 1.0, w: 4.5, h: 0.38, fill: { color: C.darkBlue } });
  s.addText("四大核心发现", { x: 0.3, y: 1.0, w: 4.5, h: 0.38, fontSize: 14, fontFace: "Microsoft YaHei", color: C.white, bold: true, align: "center", valign: "middle" });
  const findings = [
    "① 均等化方向正确：低自给率省份人均转移支付是高自给率的5.4倍（p < 0.001）",
    "② 地区差距依然严峻：人均GDP京/甘相差4倍，转移支付托底但无法根本改变经济格局",
    "③ 整体依赖加深：全国平均依赖度从37%升至47%，地方税源建设仍是长期课题",
    "④ 三类划分有效：ANOVA F=62.10，组间差异极显著，分类施策具有统计依据",
  ];
  findings.forEach((f, i) => {
    s.addText(f, { x: 0.4, y: 1.55 + i * 0.72, w: 4.3, h: 0.6, fontSize: 10, fontFace: "Microsoft YaHei", color: C.dark, valign: "middle" });
  });

  // 右侧：政策启示
  s.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.0, w: 4.5, h: 0.38, fill: { color: C.navy } });
  s.addText("政策启示", { x: 5.2, y: 1.0, w: 4.5, h: 0.38, fontSize: 14, fontFace: "Microsoft YaHei", color: C.white, bold: true, align: "center", valign: "middle" });
  const policies = [
    "① 分类优化转移支付：一般性向低自给率倾斜，专项引入绩效竞争机制",
    "② 推动地方税源建设：培育地方主体税种，增强自主造血能力",
    "③ 建立动态监测体系：面板数据年度跟踪，差异化帮扶避免一刀切",
  ];
  policies.forEach((p, i) => {
    s.addText(p, { x: 5.3, y: 1.55 + i * 0.8, w: 4.3, h: 0.6, fontSize: 10, fontFace: "Microsoft YaHei", color: C.dark, valign: "middle" });
  });

  // 底部：研究局限
  s.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 4.55, w: 9.4, h: 0.38, fill: { color: C.offWhite } });
  s.addText("局限与展望：转移支付未区分一般性/专项 → 未引入教育/医疗等社会指标 → 未来引入固定效应面板回归模型", {
    x: 0.5, y: 4.55, w: 9, h: 0.38, fontSize: 10, fontFace: "Microsoft YaHei", color: C.gray, valign: "middle",
  });
}

// ================================================================
// Slide 10: AI协作总结
// ================================================================
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  sectionTitle(s, "方法论反思：AI辅助开发的实践启示");

  // 流程统计
  statBox(s, 0.5, 1.05, 2.8, "80+ 条", "累计指令/反馈", C.navy);
  statBox(s, 3.5, 1.05, 2.8, "~1000行", "Python代码", C.blue);
  statBox(s, 6.5, 1.05, 2.8, "~4小时", "从0到交付", C.green);

  // 核心观点
  const insights = [
    { num: "1", title: "AI降低技术门槛，人定义问题边界", desc: "选题方向、指标体系、结论判断均由人拍板。AI负责代码生成和技术实现，效率提升约8倍（30h→4h）" },
    { num: "2", title: "领域知识是不可替代的质量底线", desc: "计划单列市跳过规则、决算滞后回退逻辑、西藏88%依赖度的常识校验——人的判断是校准器" },
    { num: "3", title: "迭代优于一次到位，兜底方案至关重要", desc: "可视化模块5轮调试：Plotly→px.choropleth→go.Figure→geopandas PNG，CDP验证通过≠用户本地可用" },
    { num: "4", title: "计算思维的核心是问题分解与验证", desc: "分解→协作→验证的循环才是课程核心收获，工具（Python/AI）只是这一思维的载体" },
  ];
  insights.forEach((p, i) => {
    const iy = 2.25 + i * 0.7;
    s.addShape(pres.shapes.OVAL, { x: 0.5, y: iy + 0.1, w: 0.38, h: 0.38, fill: { color: C.blue } });
    s.addText(p.num, { x: 0.5, y: iy + 0.1, w: 0.38, h: 0.38, fontSize: 13, color: C.white, bold: true, align: "center", valign: "middle" });
    s.addText(p.title, { x: 1.05, y: iy, w: 3.2, h: 0.3, fontSize: 13, fontFace: "Microsoft YaHei", color: C.darkBlue, bold: true, valign: "middle" });
    s.addText(p.desc, { x: 1.05, y: iy + 0.3, w: 8.5, h: 0.35, fontSize: 10, fontFace: "Microsoft YaHei", color: C.gray, valign: "top" });
  });

  // 底部金句
  s.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 5.1, w: 9.4, h: 0.35, fill: { color: C.offWhite } });
  s.addText("核心启示：AI降低了技术门槛，但问题定义权、数据理解力、结论判断力——因为AI的存在反而更加重要", {
    x: 0.5, y: 5.1, w: 9, h: 0.35, fontSize: 11, fontFace: "Microsoft YaHei", color: C.darkBlue, bold: true, align: "center", valign: "middle",
  });
}

// ================================================================
// 保存
// ================================================================
pres.writeFile({ fileName: path.join(OUT_DIR, "课堂演示.pptx") }).then(() => {
  console.log("PPT saved to: " + path.join(OUT_DIR, "课堂演示.pptx"));
});
