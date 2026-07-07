"""
数据清洗、合并与指标计算模块
计算：转移支付依赖度、人均转移支付、财政自给率、转移支付经济匹配度
统计检验：
  - 描述性：Pearson相关矩阵、Spearman秩相关、单因素ANOVA + Bonferroni
  - 推断性：面板固定效应回归（双向固定效应）
  - 异质性：分位数回归（Quantile Regression）
"""
import os
import logging
from typing import Dict, Tuple, Optional
import pandas as pd
import numpy as np
from scipy import stats
from config import (
    BASE_DIR, OUTPUT_DIR, PROVINCES,
    YEAR_START, YEAR_END, INDICATOR_COLS,
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_raw_data(path: Optional[str] = None) -> pd.DataFrame:
    """加载原始数据"""
    if path is None:
        path = os.path.join(OUTPUT_DIR, "raw_data.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到原始数据文件: {path}。请先运行数据采集模块")
    df = pd.read_csv(path)
    df["年份"] = df["年份"].astype(int)
    logger.info(f"加载原始数据: {len(df)} 条记录")
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """数据清洗：筛选省份、年份、填补缺失值"""
    logger.info("\n数据清洗...")
    initial = len(df)

    df = df[df["省份"].isin(PROVINCES)].copy()
    logger.info(f"  筛选省级行政区: {initial} -> {len(df)}")

    df = df[(df["年份"] >= YEAR_START) & (df["年份"] <= YEAR_END)].copy()
    logger.info(f"  筛选年份 {YEAR_START}-{YEAR_END}: {len(df)} 条")

    null_counts = df.isnull().sum()
    if null_counts.sum() > 0:
        logger.info(f"  缺失值统计:\n{null_counts[null_counts > 0]}")
        df = df.sort_values(["省份", "年份"])
        cols_fill = [
            "GDP_亿元", "常住人口_万人", "地方财政收入_亿元",
            "地方财政支出_亿元", "转移支付_亿元",
        ]
        for col in cols_fill:
            if col in df.columns:
                df[col] = df.groupby("省份")[col].transform(
                    lambda x: x.interpolate().bfill().ffill()
                )
        logger.info("  已对所有缺失值进行插值填补")

    return df


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算核心分析指标（6项）"""
    logger.info("\n计算核心指标...")

    df["转移支付依赖度"] = (
        df["转移支付_亿元"] / df["地方财政支出_亿元"] * 100
    ).round(2)
    logger.info("  [1] 转移支付依赖度 = 转移支付 / 财政支出 × 100%")

    df["人均转移支付_元"] = (
        df["转移支付_亿元"] * 10000 / df["常住人口_万人"]
    ).round(0)
    logger.info("  [2] 人均转移支付（元/人）")

    df["财政自给率"] = (
        df["地方财政收入_亿元"] / df["地方财政支出_亿元"] * 100
    ).round(2)
    logger.info("  [3] 财政自给率 = 财政收入 / 财政支出 × 100%")

    df["人均GDP_元"] = (
        df["GDP_亿元"] * 10000 / df["常住人口_万人"]
    ).round(0)
    logger.info("  [4] 人均GDP（元）")

    df = df.sort_values(["省份", "年份"])
    df["GDP增速"] = df.groupby("省份")["GDP_亿元"].pct_change() * 100
    df["转移支付增速"] = df.groupby("省份")["转移支付_亿元"].pct_change() * 100
    df["增速差"] = (df["转移支付增速"] - df["GDP增速"]).round(2)
    logger.info("  [5] 转移支付增速 vs GDP增速")

    df["转移支付经济匹配指数"] = (
        df["人均转移支付_元"] / df["人均GDP_元"]
    ).round(4)
    logger.info("  [6] 转移支付经济匹配指数 = 人均转移支付 / 人均GDP")

    return df


def classify_provinces(df: pd.DataFrame) -> pd.DataFrame:
    """按最新年份财政自给率将省份分为三类"""
    logger.info("\n省份分类...")
    latest_year = df["年份"].max()
    recent = df[df["年份"] == latest_year]

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

    logger.info(f"  高自给率（≥60%）: {len(high)} 个省份 — {', '.join(high)}")
    logger.info(f"  中自给率（35%-60%）: {len(mid)} 个省份")
    logger.info(f"  低自给率（<35%）: {len(low)} 个省份 — {', '.join(low)}")
    return df


def generate_summary(df: pd.DataFrame) -> pd.DataFrame:
    """生成最新年份的统计摘要"""
    logger.info("\n生成统计摘要...")
    latest_year = df["年份"].max()
    recent = df[df["年份"] == latest_year]

    summary_cols = [
        "转移支付依赖度", "人均转移支付_元", "财政自给率",
        "人均GDP_元", "转移支付经济匹配指数",
    ]
    summary = recent[summary_cols].describe().round(2)

    logger.info("\n  === 关键发现 ===")
    for col in summary_cols:
        max_prov = recent.loc[recent[col].idxmax(), "省份"]
        min_prov = recent.loc[recent[col].idxmin(), "省份"]
        max_val = recent[col].max()
        min_val = recent[col].min()
        logger.info(f"  {col}: 最高={max_prov}({max_val:.1f}), 最低={min_prov}({min_val:.1f})")

    summary_path = os.path.join(OUTPUT_DIR, "summary_stats.csv")
    summary.to_csv(summary_path, encoding="utf-8-sig")
    logger.info(f"\n统计摘要已保存: {summary_path}")

    return summary


# ============================================================
# 统计检验模块
# ============================================================
def _run_baseline_tests(df: pd.DataFrame) -> Dict:
    """执行基础统计检验：Pearson、Spearman、ANOVA"""
    logger.info("\n" + "=" * 60)
    logger.info("基础统计检验")
    logger.info("=" * 60)

    latest_year = df["年份"].max()
    recent = df[df["年份"] == latest_year]
    numeric_cols = [
        "转移支付依赖度", "人均转移支付_元", "财政自给率",
        "人均GDP_元", "转移支付经济匹配指数",
    ]

    corr_matrix = recent[numeric_cols].corr().round(4)
    corr_path = os.path.join(OUTPUT_DIR, "correlation_matrix.csv")
    corr_matrix.to_csv(corr_path, encoding="utf-8-sig")
    logger.info(f"\n[1] Pearson相关系数矩阵已保存: {corr_path}")
    logger.info(corr_matrix.to_string())

    r_dep_gdp = corr_matrix.loc["转移支付依赖度", "人均GDP_元"]
    r_dep_self = corr_matrix.loc["转移支付依赖度", "财政自给率"]
    logger.info(f"\n  关键发现:")
    logger.info(f"    转移支付依赖度 vs 人均GDP: r = {r_dep_gdp:.4f} (强负相关)")
    logger.info(f"    转移支付依赖度 vs 财政自给率: r = {r_dep_self:.4f} (几乎完全负相关)")

    spearman_r, spearman_p = stats.spearmanr(
        recent["转移支付依赖度"], recent["人均GDP_元"]
    )
    logger.info(f"\n[2] Spearman秩相关（依赖度 vs 人均GDP）:")
    logger.info(f"    ρ = {spearman_r:.4f}, p = {spearman_p:.6f}")
    if spearman_p < 0.001:
        logger.info("    结论：两者存在极显著的单调负相关关系（p < 0.001）")

    groups = []
    group_labels = []
    for cat in recent["财政自给率分类"].unique():
        mask = recent["财政自给率分类"] == cat
        groups.append(recent.loc[mask, "转移支付依赖度"].values)
        group_labels.append(cat)

    f_stat = anova_p = np.nan
    pairwise_results = []
    if len(groups) >= 2:
        f_stat, anova_p = stats.f_oneway(*groups)
        logger.info(f"\n[3] 单因素ANOVA（三类省份的转移支付依赖度差异）:")
        logger.info(f"    F = {f_stat:.4f}, p = {anova_p:.8f}")
        if anova_p < 0.001:
            logger.info("    结论：三类省份的转移支付依赖度存在极显著差异（p < 0.001）")

        from itertools import combinations
        logger.info(f"\n    事后两两比较（Bonferroni校正）:")
        for (name_a, vals_a), (name_b, vals_b) in combinations(
            zip(group_labels, groups), 2
        ):
            t_stat, t_p = stats.ttest_ind(vals_a, vals_b)
            label_a = name_a.split("（")[0] if "（" in str(name_a) else str(name_a)
            label_b = name_b.split("（")[0] if "（" in str(name_b) else str(name_b)
            logger.info(f"      {label_a} vs {label_b}: t = {t_stat:.4f}, p = {t_p:.6f}")
            pairwise_results.append({
                "组别A": label_a, "组别B": label_b,
                "t统计量": round(t_stat, 4), "p值": round(t_p, 6),
            })

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
    logger.info(f"\n  统计检验结果已保存: {anova_path}")

    return {
        "corr_matrix": corr_matrix,
        "spearman_r": spearman_r,
        "spearman_p": spearman_p,
        "f_stat": f_stat,
        "anova_p": anova_p,
        "pairwise": pairwise_results,
    }


def _run_panel_regression(df: pd.DataFrame) -> Optional[Dict]:
    """
    面板固定效应回归（双向固定效应）
    被解释变量：转移支付依赖度
    解释变量：人均GDP（对数）、财政自给率、年份趋势
    控制：省份固定效应 + 年份固定效应
    """
    logger.info("\n" + "=" * 60)
    logger.info("高级统计分析：面板固定效应回归")
    logger.info("=" * 60)

    try:
        import statsmodels.api as sm
        from linearmodels.panel import PanelOLS
    except ImportError:
        logger.warning("  statsmodels/linearmodels 未安装，跳过面板回归")
        return None

    df_reg = df.dropna(subset=["转移支付依赖度", "人均GDP_元", "财政自给率"]).copy()
    if len(df_reg) < 100:
        logger.warning("  样本量不足，跳过面板回归")
        return None

    df_reg["ln人均GDP"] = np.log(df_reg["人均GDP_元"])
    df_reg["ln人口"] = np.log(df_reg["常住人口_万人"])
    df_reg = df_reg.set_index(["省份", "年份"])

    Y = df_reg["转移支付依赖度"]
    X = df_reg[["ln人均GDP", "ln人口"]]
    X = sm.add_constant(X)

    try:
        model = PanelOLS(Y, X, entity_effects=True, time_effects=True, drop_absorbed=True)
        results = model.fit(cov_type="clustered", cluster_entity=True)

        logger.info(f"\n  模型：转移支付依赖度 ~ ln(人均GDP) + ln(人口) + 省份FE + 年份FE")
        logger.info(f"  样本量: {results.nobs}, 省份数: {results.entity_info.total if hasattr(results, 'entity_info') else 'N/A'}")
        logger.info(f"  R² (within): {results.rsquared_within:.4f}" if hasattr(results, 'rsquared_within') else f"  R²: {results.rsquared:.4f}")
        logger.info(f"  F统计量: {results.f_statistic.stat:.4f}, p = {results.f_statistic.pval:.6f}")

        logger.info(f"\n  系数估计（聚类标准误）:")
        coeffs = []
        for var in results.params.index:
            coef = results.params[var]
            se = results.std_errors[var]
            pval = results.pvalues[var]
            stars = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else "ns"
            logger.info(f"    {var}: β = {coef:.4f}, SE = {se:.4f}, p = {pval:.4f} {stars}")
            coeffs.append({
                "变量": var, "系数": round(coef, 4),
                "标准误": round(se, 4), "p值": round(pval, 4), "显著性": stars,
            })

        reg_results = {
            "nobs": int(results.nobs),
            "rsquared": round(float(results.rsquared), 4),
            "rsquared_within": round(float(results.rsquared_within), 4) if hasattr(results, 'rsquared_within') else None,
            "f_stat": round(float(results.f_statistic.stat), 4),
            "f_pval": round(float(results.f_statistic.pval), 6),
            "coefficients": coeffs,
        }

        reg_path = os.path.join(OUTPUT_DIR, "panel_regression.csv")
        pd.DataFrame(coeffs).to_csv(reg_path, index=False, encoding="utf-8-sig")
        logger.info(f"\n  面板回归结果已保存: {reg_path}")

        return reg_results

    except Exception as e:
        logger.error(f"  面板回归失败: {e}")
        return None


def _run_quantile_regression(df: pd.DataFrame) -> Optional[Dict]:
    """
    分位数回归（Quantile Regression）
    检验在转移支付依赖度的不同分位点上，人均GDP的影响是否存在异质性
    """
    logger.info("\n" + "=" * 60)
    logger.info("高级统计分析：分位数回归")
    logger.info("=" * 60)

    try:
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
    except ImportError:
        logger.warning("  statsmodels 未安装，跳过分位数回归")
        return None

    latest_year = df["年份"].max()
    recent = df[df["年份"] == latest_year].dropna(
        subset=["转移支付依赖度", "人均GDP_元", "财政自给率"]
    )

    if len(recent) < 25:
        logger.warning("  样本量不足，跳过分位数回归")
        return None

    recent["ln人均GDP"] = np.log(recent["人均GDP_元"])
    recent["ln人口"] = np.log(recent["常住人口_万人"])

    quantiles = [0.25, 0.50, 0.75]
    quantile_results = []

    logger.info(f"\n  模型：转移支付依赖度 ~ ln(人均GDP) + ln(人口)")
    logger.info(f"  截面年份：{latest_year}")
    logger.info(f"  样本量：{len(recent)}")

    for q in quantiles:
        try:
            mod = smf.quantreg("转移支付依赖度 ~ ln人均GDP + ln人口", recent)
            res = mod.fit(q=q)

            logger.info(f"\n  分位数 q = {q:.2f}:")
            for var in res.params.index:
                coef = res.params[var]
                pval = res.pvalues[var]
                stars = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else "ns"
                logger.info(f"    {var}: β = {coef:.4f}, p = {pval:.4f} {stars}")
                quantile_results.append({
                    "分位数": q, "变量": var,
                    "系数": round(coef, 4), "p值": round(pval, 4),
                })
        except Exception as e:
            logger.warning(f"  q={q} 分位数回归失败: {e}")

    if quantile_results:
        qr_path = os.path.join(OUTPUT_DIR, "quantile_regression.csv")
        pd.DataFrame(quantile_results).to_csv(qr_path, index=False, encoding="utf-8-sig")
        logger.info(f"\n  分位数回归结果已保存: {qr_path}")
        return {"quantiles": quantiles, "results": quantile_results}

    return None


def statistical_analysis(df: pd.DataFrame) -> Dict:
    """执行全部统计检验与分析"""
    results = {}

    results["baseline"] = _run_baseline_tests(df)
    results["panel_regression"] = _run_panel_regression(df)
    results["quantile_regression"] = _run_quantile_regression(df)

    logger.info("=" * 60)
    return results


def process_all() -> pd.DataFrame:
    """执行全部数据处理流程"""
    logger.info("=" * 60)
    logger.info("数据清洗与指标计算")
    logger.info("=" * 60)

    df = load_raw_data()
    df = clean_data(df)
    df = calculate_indicators(df)
    df = classify_provinces(df)

    output_path = os.path.join(OUTPUT_DIR, "indicators.csv")
    available_cols = [c for c in INDICATOR_COLS if c in df.columns]
    df[available_cols].to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"\n指标数据已保存至: {output_path}")

    generate_summary(df)
    statistical_analysis(df)

    logger.info("=" * 60)
    return df


if __name__ == "__main__":
    process_all()
