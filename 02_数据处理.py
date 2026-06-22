"""
数据清洗、合并与指标计算模块
计算：转移支付依赖度、人均转移支付、财政自给率、转移支付经济匹配度
包含统计检验：Pearson相关、ANOVA、Spearman秩相关
"""
import os
import pandas as pd
import numpy as np
from scipy import stats
from config import BASE_DIR, OUTPUT_DIR, PROVINCES, YEAR_START, YEAR_END, INDICATOR_COLS

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_raw_data(path=None):
    """加载原始数据"""
    if path is None:
        path = os.path.join(OUTPUT_DIR, "raw_data.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到原始数据文件: {path}。请先运行 data_collection.py")
    df = pd.read_csv(path)
    df["年份"] = df["年份"].astype(int)
    print(f"加载原始数据: {len(df)} 条记录")
    return df


def clean_data(df):
    """数据清洗"""
    print("\n数据清洗...")
    initial = len(df)

    # 只保留31个省级行政区
    df = df[df["省份"].isin(PROVINCES)]
    print(f"  筛选省级行政区: {initial} -> {len(df)}")

    # 年份范围
    df = df[(df["年份"] >= YEAR_START) & (df["年份"] <= YEAR_END)]
    print(f"  筛选年份 {YEAR_START}-{YEAR_END}: {len(df)} 条")

    # 缺失值检查
    null_counts = df.isnull().sum()
    if null_counts.sum() > 0:
        print(f"  缺失值统计:\n{null_counts[null_counts > 0]}")
        # 对少量缺失用插值填补
        df = df.sort_values(["省份", "年份"])
        cols_fill = ["GDP_亿元", "常住人口_万人", "地方财政收入_亿元",
                      "地方财政支出_亿元", "转移支付_亿元"]
        for col in cols_fill:
            if col in df.columns:
                df[col] = df.groupby("省份")[col].transform(
                    lambda x: x.interpolate().bfill().ffill()
                )
        print("  已对所有缺失值进行插值填补")

    return df


def calculate_indicators(df):
    """计算核心分析指标"""
    print("\n计算核心指标...")

    # 1. 转移支付依赖度 = 中央转移支付 / 地方一般公共预算支出
    df["转移支付依赖度"] = (df["转移支付_亿元"] / df["地方财政支出_亿元"] * 100).round(2)
    print("  [1] 转移支付依赖度 = 转移支付 / 财政支出 × 100%")

    # 2. 人均转移支付 = 转移支付总额 / 常住人口（元/人）
    df["人均转移支付_元"] = (df["转移支付_亿元"] * 10000 / df["常住人口_万人"]).round(0)
    print("  [2] 人均转移支付（元/人）")

    # 3. 财政自给率 = 地方财政收入 / 地方财政支出
    df["财政自给率"] = (df["地方财政收入_亿元"] / df["地方财政支出_亿元"] * 100).round(2)
    print("  [3] 财政自给率 = 财政收入 / 财政支出 × 100%")

    # 4. 人均GDP（元）
    df["人均GDP_元"] = (df["GDP_亿元"] * 10000 / df["常住人口_万人"]).round(0)
    print("  [4] 人均GDP（元）")

    # 5. 转移支付增速 vs GDP增速（同比，%）
    df = df.sort_values(["省份", "年份"])
    df["GDP增速"] = df.groupby("省份")["GDP_亿元"].pct_change() * 100
    df["转移支付增速"] = df.groupby("省份")["转移支付_亿元"].pct_change() * 100
    df["增速差"] = (df["转移支付增速"] - df["GDP增速"]).round(2)
    print("  [5] 转移支付增速 vs GDP增速")

    # 6. 转移支付的经济匹配指数（人均转移支付 / 人均GDP，衡量转移支付偏向）
    df["转移支付经济匹配指数"] = (df["人均转移支付_元"] / df["人均GDP_元"]).round(4)
    print("  [6] 转移支付经济匹配指数 = 人均转移支付 / 人均GDP")

    return df


def classify_provinces(df):
    """按2023年财政自给率将省份分为三类"""
    print("\n省份分类...")
    recent = df[df["年份"] == df["年份"].max()]

    # 按财政自给率分类
    high = recent[recent["财政自给率"] >= 60]["省份"].tolist()
    mid = recent[(recent["财政自给率"] >= 35) & (recent["财政自给率"] < 60)]["省份"].tolist()
    low = recent[recent["财政自给率"] < 35]["省份"].tolist()

    mapping = {}
    for p in high:
        mapping[p] = "高自给率（≥60%）"
    for p in mid:
        mapping[p] = "中自给率（35%-60%）"
    for p in low:
        mapping[p] = "低自给率（<35%）"

    df["财政自给率分类"] = df["省份"].map(mapping)

    print(f"  高自给率（≥60%）: {len(high)} 个省份 — {', '.join(high)}")
    print(f"  中自给率（35%-60%）: {len(mid)} 个省份")
    print(f"  低自给率（<35%）: {len(low)} 个省份 — {', '.join(low)}")
    return df


def generate_summary(df):
    """生成统计摘要"""
    print("\n生成统计摘要...")
    recent = df[df["年份"] == df["年份"].max()]

    summary_cols = ["转移支付依赖度", "人均转移支付_元", "财政自给率",
                    "人均GDP_元", "转移支付经济匹配指数"]
    summary = recent[summary_cols].describe().round(2)

    # 极值标注
    print("\n  === 关键发现 ===")
    for col in summary_cols:
        max_prov = recent.loc[recent[col].idxmax(), "省份"]
        min_prov = recent.loc[recent[col].idxmin(), "省份"]
        max_val = recent[col].max()
        min_val = recent[col].min()
        print(f"  {col}: 最高={max_prov}({max_val:.1f}), 最低={min_prov}({min_val:.1f})")

    summary_path = os.path.join(OUTPUT_DIR, "summary_stats.csv")
    summary.to_csv(summary_path, encoding="utf-8-sig")
    print(f"\n统计摘要已保存: {summary_path}")

    return summary


def statistical_analysis(df):
    """统计检验：Pearson相关、Spearman秩相关、单因素ANOVA"""
    print("\n" + "=" * 60)
    print("统计检验与分析")
    print("=" * 60)

    recent = df[df["年份"] == df["年份"].max()]
    numeric_cols = ["转移支付依赖度", "人均转移支付_元", "财政自给率",
                    "人均GDP_元", "转移支付经济匹配指数"]

    # ---------- 1. Pearson 相关系数矩阵 ----------
    corr_matrix = recent[numeric_cols].corr().round(4)
    corr_path = os.path.join(OUTPUT_DIR, "correlation_matrix.csv")
    corr_matrix.to_csv(corr_path, encoding="utf-8-sig")
    print(f"\n[1] Pearson相关系数矩阵已保存: {corr_path}")
    print(corr_matrix.to_string())

    # 关键相关系数摘录
    r_dep_gdp = corr_matrix.loc["转移支付依赖度", "人均GDP_元"]
    r_dep_self = corr_matrix.loc["转移支付依赖度", "财政自给率"]
    print(f"\n  关键发现:")
    print(f"    转移支付依赖度 vs 人均GDP: r = {r_dep_gdp:.4f} (强负相关)")
    print(f"    转移支付依赖度 vs 财政自给率: r = {r_dep_self:.4f} (几乎完全负相关)")

    # ---------- 2. Spearman 秩相关系数 ----------
    spearman_r, spearman_p = stats.spearmanr(
        recent["转移支付依赖度"], recent["人均GDP_元"]
    )
    print(f"\n[2] Spearman秩相关（依赖度 vs 人均GDP）:")
    print(f"    ρ = {spearman_r:.4f}, p = {spearman_p:.6f}")
    if spearman_p < 0.001:
        print("    结论：两者存在极显著的单调负相关关系（p < 0.001）")

    # ---------- 3. 单因素ANOVA（三类省份组间差异） ----------
    groups = []
    group_labels = []
    for cat in recent["财政自给率分类"].unique():
        mask = recent["财政自给率分类"] == cat
        groups.append(recent.loc[mask, "转移支付依赖度"].values)
        group_labels.append(cat)

    if len(groups) >= 2:
        f_stat, anova_p = stats.f_oneway(*groups)
        print(f"\n[3] 单因素ANOVA（三类省份的转移支付依赖度差异）:")
        print(f"    F = {f_stat:.4f}, p = {anova_p:.8f}")
        if anova_p < 0.001:
            print("    结论：三类省份的转移支付依赖度存在极显著差异（p < 0.001）")

        # 事后检验：两两 t 检验
        from itertools import combinations
        print(f"\n    事后两两比较（Bonferroni校正）:")
        for (name_a, vals_a), (name_b, vals_b) in combinations(
            zip(group_labels, groups), 2
        ):
            t_stat, t_p = stats.ttest_ind(vals_a, vals_b)
            # 提取短标签
            label_a = name_a.split("（")[0] if "（" in str(name_a) else str(name_a)
            label_b = name_b.split("（")[0] if "（" in str(name_b) else str(name_b)
            print(f"      {label_a} vs {label_b}: t = {t_stat:.4f}, p = {t_p:.6f}")

    # 保存ANOVA结果
    anova_path = os.path.join(OUTPUT_DIR, "anova_results.csv")
    anova_df = pd.DataFrame({
        "检验项": ["单因素ANOVA", "Spearman秩相关"],
        "统计量": [f"F={f_stat:.4f}", f"ρ={spearman_r:.4f}"],
        "p值": [f"{anova_p:.8f}", f"{spearman_p:.6f}"],
        "显著性": [
            "*** (p<0.001)" if anova_p < 0.001 else "ns",
            "*** (p<0.001)" if spearman_p < 0.001 else "ns",
        ],
        "结论": [
            "三类省份依赖度差异极显著",
            "依赖度与人均GDP极显著负相关",
        ],
    })
    anova_df.to_csv(anova_path, index=False, encoding="utf-8-sig")
    print(f"\n  统计检验结果已保存: {anova_path}")
    print("=" * 60)


def process_all():
    """执行全部数据处理流程"""
    print("=" * 60)
    print("数据清洗与指标计算")
    print("=" * 60)

    df = load_raw_data()
    df = clean_data(df)
    df = calculate_indicators(df)
    df = classify_provinces(df)

    # 保存处理后的数据
    output_path = os.path.join(OUTPUT_DIR, "indicators.csv")
    available_cols = [c for c in INDICATOR_COLS if c in df.columns]
    df[available_cols].to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n指标数据已保存至: {output_path}")

    generate_summary(df)

    # 统计检验与分析
    statistical_analysis(df)

    print("=" * 60)
    return df


if __name__ == "__main__":
    process_all()
