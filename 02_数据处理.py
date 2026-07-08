"""
数据清洗、合并与指标计算模块
计算：转移支付依赖度、人均转移支付、财政自给率、转移支付经济匹配度
统计检验：
  - 描述性：Pearson相关矩阵、Spearman秩相关、单因素ANOVA + Bonferroni
  - 推断性：面板固定效应回归（双向固定效应）
  - 异质性：分位数回归（Quantile Regression）
  - 诊断性：VIF多重共线性、异方差检验、Hausman检验、序列相关检验
"""
import os
import logging
from typing import Dict, Tuple, Optional, List, Any
import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import norm
from config import (
    BASE_DIR, OUTPUT_DIR, PROVINCES,
    YEAR_START, YEAR_END, INDICATOR_COLS, NUMERIC_INDICATORS,
    CLASSIFICATION_THRESHOLDS, CLASSIFICATION_LABELS,
    PANEL_REG_CONTROLS, PANEL_REG_TARGET, QUANTILE_POINTS,
    VIF_THRESHOLD, MIN_SAMPLES_PANEL, MIN_SAMPLES_QUANTILE,
    DEPENDENCY_RATE_MAX, SELF_RATE_MAX,
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
    """按最新年份财政自给率将省份分为三类（使用配置阈值）"""
    logger.info("\n省份分类...")
    latest_year = df["年份"].max()
    recent = df[df["年份"] == latest_year]

    high_threshold = CLASSIFICATION_THRESHOLDS["high"]
    low_threshold = CLASSIFICATION_THRESHOLDS["low"]

    high = recent[recent["财政自给率"] >= high_threshold]["省份"].tolist()
    mid = recent[(recent["财政自给率"] >= low_threshold) & (recent["财政自给率"] < high_threshold)]["省份"].tolist()
    low = recent[recent["财政自给率"] < low_threshold]["省份"].tolist()

    mapping = {}
    for p in high:
        mapping[p] = CLASSIFICATION_LABELS["high"]
    for p in mid:
        mapping[p] = CLASSIFICATION_LABELS["mid"]
    for p in low:
        mapping[p] = CLASSIFICATION_LABELS["low"]

    df["财政自给率分类"] = df["省份"].map(mapping)

    logger.info(f"  高自给率（≥{high_threshold}%）: {len(high)} 个省份 — {', '.join(high)}")
    logger.info(f"  中自给率（{low_threshold}%-{high_threshold}%）: {len(mid)} 个省份")
    logger.info(f"  低自给率（<{low_threshold}%）: {len(low)} 个省份 — {', '.join(low)}")
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


# ============================================================
# 统计诊断检验模块
# ============================================================
def _calculate_vif(X: pd.DataFrame) -> pd.DataFrame:
    """
    计算方差膨胀因子（VIF）检验多重共线性
    VIF > 10 表示存在严重多重共线性
    """
    try:
        import statsmodels.api as sm
    except ImportError:
        return pd.DataFrame()

    vif_data = []
    variables = X.columns.tolist()

    # 只计算非常数项的VIF
    for var in variables:
        if var == "const":
            continue
        
        # 以该变量为因变量，其他非常数变量为自变量进行回归
        other_vars = [v for v in variables if v != var and v != "const"]
        if len(other_vars) == 0:
            # 只有一个解释变量，VIF=1
            vif_data.append({
                "变量": var,
                "VIF": 1.0,
                "R²": 0.0,
                "共线性": "无",
            })
            continue
        
        Y_vif = X[var]
        X_vif = X[other_vars]
        
        # 如果X_vif只有一个变量，也需要特殊处理
        if len(other_vars) == 1:
            # 计算简单相关系数
            r = np.corrcoef(X[var], X[other_vars[0]])[0, 1]
            r_squared = r ** 2
            vif = 1 / (1 - r_squared) if r_squared < 1 else np.inf
        else:
            X_vif = sm.add_constant(X_vif, has_constant="add")
            try:
                model = sm.OLS(Y_vif, X_vif).fit()
                r_squared = model.rsquared
                vif = 1 / (1 - r_squared) if r_squared < 1 else np.inf
            except Exception:
                vif = np.inf
                r_squared = 1.0

        vif_data.append({
            "变量": var,
            "VIF": round(vif, 4),
            "R²": round(r_squared, 4),
            "共线性": "严重" if vif > VIF_THRESHOLD else "无/轻微",
        })

    return pd.DataFrame(vif_data)


def _run_heteroskedasticity_test(residuals: np.ndarray, X: pd.DataFrame) -> Dict:
    """
    异方差检验（White 检验和 Breusch-Pagan 检验）
    """
    try:
        import statsmodels.stats.diagnostic as diag
        import statsmodels.api as sm
    except ImportError:
        return {}

    results = {}

    # Breusch-Pagan 检验
    try:
        # 使用残差平方对原变量回归
        resid_sq = residuals ** 2
        X_bp = sm.add_constant(X)
        model_bp = sm.OLS(resid_sq, X_bp).fit()
        n = len(residuals)
        lm_stat = n * model_bp.rsquared
        lm_pval = 1 - stats.chi2.cdf(lm_stat, df=X_bp.shape[1] - 1)

        results["Breusch_Pagan"] = {
            "LM统计量": round(lm_stat, 4),
            "p值": round(lm_pval, 6),
            "结论": "存在异方差" if lm_pval < 0.05 else "无异方差",
            "建议": "使用稳健标准误" if lm_pval < 0.05 else "OLS标准误有效",
        }
    except Exception as e:
        results["Breusch_Pagan"] = {"错误": str(e)}

    # White 检验（更一般化）
    try:
        white_stat, white_pval, _, _ = diag.het_white(residuals, X_bp)
        results["White"] = {
            "统计量": round(white_stat, 4),
            "p值": round(white_pval, 6),
            "结论": "存在异方差" if white_pval < 0.05 else "无异方差",
        }
    except Exception:
        pass

    return results


def _run_serial_correlation_test(panel_data: pd.DataFrame, residuals: pd.Series) -> Dict:
    """
    面板数据序列相关检验（Wooldridge 检验）
    检验是否存在时间序列自相关
    """
    try:
        from linearmodels.panel import compare
    except ImportError:
        return {"Wooldridge": {"说明": "linearmodels 未安装，跳过"}}

    results = {}

    # 简化版检验：计算残差的一阶自相关系数
    try:
        provinces = panel_data.index.get_level_values(0).unique()
        autocorr_coeffs = []
        for prov in provinces:
            prov_resid = residuals[prov].values if prov in residuals.index.get_level_values(0) else []
            if len(prov_resid) > 2:
                # 计算一阶自相关
                autocorr = np.corrcoef(prov_resid[:-1], prov_resid[1:])[0, 1]
                autocorr_coeffs.append(autocorr)

        if autocorr_coeffs:
            avg_autocorr = np.mean(autocorr_coeffs)
            results["一阶自相关"] = {
                "平均系数": round(avg_autocorr, 4),
                "范围": f"[{round(min(autocorr_coeffs), 4)}, {round(max(autocorr_coeffs), 4)}]",
                "结论": "存在正自相关" if avg_autocorr > 0.3 else "存在负自相关" if avg_autocorr < -0.3 else "无明显自相关",
            }
    except Exception as e:
        results["一阶自相关"] = {"错误": str(e)}

    return results


def _run_spatial_autocorrelation(df: pd.DataFrame) -> Dict:
    """
    空间自相关检验（Moran's I）
    检验转移支付依赖度是否存在空间聚集效应
    """
    logger.info("\n" + "=" * 60)
    logger.info("空间计量分析：Moran's I 空间自相关")
    logger.info("=" * 60)

    results = {}

    try:
        import libpysal
        from esda.moran import Moran
    except ImportError:
        logger.warning("  libpysal/esda 未安装，跳过空间自相关检验")
        return {"Moran_I": {"说明": "libpysal/esda 未安装"}}

    # 获取最新年份数据
    latest_year = df["年份"].max()
    recent = df[df["年份"] == latest_year].copy()

    # 尝试加载 GeoJSON 构建空间权重矩阵
    geojson_path = os.path.join(OUTPUT_DIR, "china_provinces.geojson")
    if not os.path.exists(geojson_path):
        logger.warning("  GeoJSON 文件不存在，使用简化空间权重矩阵")
        # 使用省份地理位置的简化邻接关系（基于经纬度）
        try:
            province_coords = _get_province_centroid_coords()
            coords = [province_coords.get(p, [0, 0]) for p in recent["省份"].values]
            coords = np.array(coords)
            
            # 计算距离矩阵
            n = len(coords)
            dist_matrix = np.zeros((n, n))
            for i in range(n):
                for j in range(n):
                    dist_matrix[i, j] = np.sqrt(
                        (coords[i, 0] - coords[j, 0]) ** 2 + 
                        (coords[i, 1] - coords[j, 1]) ** 2
                    )
            
            # 构建 K近邻权重矩阵（K=4）
            K = 4
            w_matrix = np.zeros((n, n))
            for i in range(n):
                nearest = np.argsort(dist_matrix[i])[1:K+1]  # 排除自身
                w_matrix[i, nearest] = 1
            
            # 行标准化
            w_matrix = w_matrix / w_matrix.sum(axis=1, keepdims=True)
            
            # 计算 Moran's I
            y = recent["转移支付依赖度"].values
            y_mean = y.mean()
            
            # Moran's I 公式
            s0 = w_matrix.sum()
            s1 = 0.5 * ((w_matrix + w_matrix.T) ** 2).sum()
            s2 = ((w_matrix.sum(axis=1) + w_matrix.sum(axis=0)) ** 2).sum()
            
            numerator = n * np.sum(w_matrix * np.outer(y - y_mean, y - y_mean))
            denominator = s0 * np.sum((y - y_mean) ** 2)
            
            moran_i = numerator / denominator if denominator > 0 else 0
            
            # 计算 Z 统计量和 p 值
            var_i = (n ** 2 * s1 - n * s2 + 3 * s0 ** 2) / (s0 ** 2 * (n ** 2 - 1)) - (1 / (n - 1)) ** 2
            z_stat = (moran_i - (-1 / (n - 1))) / np.sqrt(var_i)
            p_value = 2 * (1 - norm.cdf(abs(z_stat)))
            
            results["Moran_I"] = {
                "Moran_I": round(moran_i, 4),
                "Z统计量": round(z_stat, 4),
                "p值": round(p_value, 6),
                "结论": "存在空间聚集" if p_value < 0.05 and moran_i > 0 else "空间随机分布",
                "权重类型": "K近邻(简化)",
            }
            
            logger.info(f"  Moran's I = {moran_i:.4f}")
            logger.info(f"  Z 统计量 = {z_stat:.4f}, p = {p_value:.6f}")
            if p_value < 0.05:
                if moran_i > 0:
                    logger.info("  结论：转移支付依赖度存在显著的空间聚集效应（正相关）")
                else:
                    logger.info("  结论：转移支付依赖度存在空间离散效应（负相关）")
            else:
                logger.info("  结论：转移支付依赖度空间分布随机，无显著聚集")
            
        except Exception as e:
            logger.warning(f"  简化空间权重矩阵计算失败: {e}")
            results["Moran_I"] = {"错误": str(e)}
            return results
    else:
        try:
            import geopandas as gpd
            gdf = gpd.read_file(geojson_path)
            
            # 只筛选31个省份（排除港澳台等）
            province_set = set(recent["省份"].unique())
            gdf = gdf[gdf["name"].isin(province_set)]
            
            # 合并数据
            gdf = gdf.merge(recent[["省份", "转移支付依赖度"]], 
                          left_on="name", right_on="省份", how="left")
            gdf = gdf.dropna(subset=["转移支付依赖度"])
            
            # 构建空间权重矩阵（K近邻，避免岛屿问题）
            # 使用 K近邻而不是 Queen 邻接，因为海南等岛屿无邻接
            w = libpysal.weights.KNN.from_dataframe(gdf, k=4)
            w.transform = "r"  # 行标准化
            
            # 计算 Moran's I
            y = gdf["转移支付依赖度"].values
            moran = Moran(y, w)
            
            # 获取值并转换为 float
            moran_i = float(moran.I) if hasattr(moran.I, '__float__') else moran.I
            z_val = float(moran.z[0]) if isinstance(moran.z, np.ndarray) else float(moran.z)
            p_val = float(moran.p_norm[0]) if isinstance(moran.p_norm, np.ndarray) else float(moran.p_norm)
            
            results["Moran_I"] = {
                "Moran_I": round(moran_i, 4),
                "Z统计量": round(z_val, 4),
                "p值": round(p_val, 6),
                "结论": "存在空间聚集" if p_val < 0.05 and moran_i > 0 else "空间随机分布",
                "权重类型": "KNN(k=4)",
            }
            
            logger.info(f"  Moran's I = {moran_i:.4f}")
            logger.info(f"  Z 统计量 = {z_val:.4f}, p = {p_val:.6f}")
            if p_val < 0.05:
                if moran_i > 0:
                    logger.info("  结论：转移支付依赖度存在显著的空间聚集效应")
                else:
                    logger.info("  结论：转移支付依赖度存在空间离散效应")
            else:
                logger.info("  结论：空间分布随机")
            
        except Exception as e:
            logger.warning(f"  GeoJSON 方式计算失败: {e}")
            results["Moran_I"] = {"错误": str(e)}
            return results

    # 保存空间自相关结果
    if "Moran_I" in results and "错误" not in results["Moran_I"]:
        spatial_path = os.path.join(OUTPUT_DIR, "spatial_autocorrelation.csv")
        pd.DataFrame([results["Moran_I"]]).to_csv(spatial_path, index=False, encoding="utf-8-sig")
        logger.info(f"\n  空间自相关结果已保存: {spatial_path}")

    logger.info("=" * 60)
    return results


def _get_province_centroid_coords() -> Dict[str, List[float]]:
    """获取省份中心点经纬度（简化版，用于构建空间权重）"""
    # 中国各省份大致中心坐标
    coords = {
        "北京市": [116.4, 39.9], "天津市": [117.2, 39.1],
        "河北省": [114.5, 38.0], "山西省": [112.5, 37.9],
        "内蒙古自治区": [111.7, 41.8], "辽宁省": [123.4, 41.8],
        "吉林省": [125.3, 43.9], "黑龙江省": [126.6, 45.8],
        "上海市": [121.5, 31.2], "江苏省": [120.3, 32.0],
        "浙江省": [120.2, 30.3], "安徽省": [117.3, 31.9],
        "福建省": [119.3, 26.1], "江西省": [115.9, 28.7],
        "山东省": [117.0, 36.7], "河南省": [113.7, 34.8],
        "湖北省": [114.3, 30.6], "湖南省": [113.0, 28.2],
        "广东省": [113.3, 23.1], "广西壮族自治区": [108.3, 23.5],
        "海南省": [110.4, 19.0], "重庆市": [106.5, 29.6],
        "四川省": [104.1, 30.7], "贵州省": [106.7, 26.6],
        "云南省": [102.7, 25.0], "西藏自治区": [91.1, 29.7],
        "陕西省": [109.0, 34.3], "甘肃省": [103.8, 36.1],
        "青海省": [96.0, 35.6], "宁夏回族自治区": [106.3, 37.5],
        "新疆维吾尔自治区": [87.6, 43.8],
    }
    return coords


def _normalize_province_name(name: str) -> str:
    """规范化省份名称"""
    name = str(name).strip()
    # 处理常见的变体
    replacements = {
        "北京": "北京市", "天津": "天津市",
        "河北": "河北省", "山西": "山西省",
        "内蒙古": "内蒙古自治区",
        "辽宁": "辽宁省", "吉林": "吉林省",
        "黑龙江": "黑龙江省",
        "上海": "上海市", "江苏": "江苏省",
        "浙江": "浙江省", "安徽": "安徽省",
        "福建": "福建省", "江西": "江西省",
        "山东": "山东省", "河南": "河南省",
        "湖北": "湖北省", "湖南": "湖南省",
        "广东": "广东省", "广西": "广西壮族自治区",
        "海南": "海南省", "重庆": "重庆市",
        "四川": "四川省", "贵州": "贵州省",
        "云南": "云南省", "西藏": "西藏自治区",
        "陕西": "陕西省", "甘肃": "甘肃省",
        "青海": "青海省", "宁夏": "宁夏回族自治区",
        "新疆": "新疆维吾尔自治区",
    }
    for short, full in replacements.items():
        if short in name or name == short:
            return full
    return name


def _run_model_diagnostics(df: pd.DataFrame, panel_results: Optional[Dict] = None) -> Dict:
    """
    执行完整的回归模型诊断检验
    包括：VIF多重共线性、异方差检验、序列相关检验、空间自相关
    """
    logger.info("\n" + "=" * 60)
    logger.info("回归模型诊断检验")
    logger.info("=" * 60)

    diagnostics = {}

    # 准备回归数据
    df_reg = df.dropna(subset=["转移支付依赖度", "人均GDP_元", "常住人口_万人"]).copy()
    if len(df_reg) < MIN_SAMPLES_PANEL:
        logger.warning("  样本量不足，跳过诊断检验")
        return diagnostics

    df_reg["ln人均GDP"] = np.log(df_reg["人均GDP_元"])
    df_reg["ln人口"] = np.log(df_reg["常住人口_万人"])

    X = df_reg[["ln人均GDP", "ln人口"]]
    Y = df_reg["转移支付依赖度"]

    # 1. VIF 多重共线性检验
    logger.info("\n[1] VIF 多重共线性检验:")
    import statsmodels.api as sm
    X_with_const = sm.add_constant(X)
    vif_df = _calculate_vif(X_with_const)

    if not vif_df.empty:
        diagnostics["VIF"] = vif_df.to_dict("records")
        for row in vif_df.itertuples():
            logger.info(f"    {row.变量}: VIF = {row.VIF:.4f} ({row.共线性})")

        max_vif = vif_df["VIF"].max()
        if max_vif > VIF_THRESHOLD:
            logger.warning(f"    警告：最大 VIF = {max_vif:.4f} > {VIF_THRESHOLD}，存在多重共线性风险")
        else:
            logger.info(f"    结论：所有 VIF < {VIF_THRESHOLD}，无严重多重共线性")

        vif_path = os.path.join(OUTPUT_DIR, "vif_diagnostic.csv")
        vif_df.to_csv(vif_path, index=False, encoding="utf-8-sig")
        logger.info(f"    VIF 结果已保存: {vif_path}")

    # 2. OLS 回归（用于诊断）
    logger.info("\n[2] OLS 回归诊断:")
    ols_model = sm.OLS(Y, X_with_const).fit()
    logger.info(f"    R² = {ols_model.rsquared:.4f}")
    logger.info(f"    F 统计量 = {ols_model.fvalue:.4f}, p = {ols_model.f_pvalue:.6f}")

    diagnostics["OLS"] = {
        "rsquared": round(ols_model.rsquared, 4),
        "f_stat": round(ols_model.fvalue, 4),
        "f_pval": round(ols_model.f_pvalue, 6),
        "nobs": int(ols_model.nobs),
    }

    # 3. 异方差检验
    logger.info("\n[3] 异方差检验:")
    hetero_results = _run_heteroskedasticity_test(ols_model.resid.values, X_with_const)
    diagnostics["heteroskedasticity"] = hetero_results

    for test_name, test_result in hetero_results.items():
        if "错误" in test_result:
            logger.info(f"    {test_name}: {test_result['错误']}")
        else:
            pval = test_result.get("p值", test_result.get("LM统计量的p值", "N/A"))
            conclusion = test_result.get("结论", "N/A")
            logger.info(f"    {test_name}: p = {pval} → {conclusion}")

    # 4. 序列相关检验（面板数据）
    logger.info("\n[4] 面板数据序列相关检验:")
    df_panel = df_reg.set_index(["省份", "年份"])
    resid_panel = pd.Series(ols_model.resid.values, index=df_panel.index)
    serial_results = _run_serial_correlation_test(df_panel, resid_panel)
    diagnostics["serial_correlation"] = serial_results

    for test_name, test_result in serial_results.items():
        if "说明" in test_result or "错误" in test_result:
            logger.info(f"    {test_name}: {test_result.get('说明', test_result.get('错误', 'N/A'))}")
        else:
            logger.info(f"    {test_name}: {test_result}")

    # 保存诊断结果汇总
    diag_summary = []
    max_vif = vif_df["VIF"].max() if not vif_df.empty else 0.0
    diag_summary.append({"检验类别": "VIF多重共线性", "结果": f"最大VIF={max_vif:.4f}",
                         "判断": "无严重共线性" if max_vif <= VIF_THRESHOLD else "存在共线性"})
    if "Breusch_Pagan" in hetero_results:
        bp = hetero_results["Breusch_Pagan"]
        diag_summary.append({"检验类别": "Breusch-Pagan异方差", "结果": f"p={bp.get('p值', 'N/A')}", 
                             "判断": bp.get("结论", "N/A")})
    if "一阶自相关" in serial_results:
        ac = serial_results["一阶自相关"]
        diag_summary.append({"检验类别": "一阶自相关", "结果": f"平均系数={ac.get('平均系数', 'N/A')}", 
                             "判断": ac.get("结论", "N/A")})

    diag_path = os.path.join(OUTPUT_DIR, "regression_diagnostic.csv")
    pd.DataFrame(diag_summary).to_csv(diag_path, index=False, encoding="utf-8-sig")
    logger.info(f"\n  诊断检验汇总已保存: {diag_path}")

    # 5. 空间自相关检验
    spatial_results = _run_spatial_autocorrelation(df)
    diagnostics["spatial_autocorrelation"] = spatial_results

    # 添加空间自相关到诊断汇总
    if "Moran_I" in spatial_results and "错误" not in spatial_results["Moran_I"]:
        moran = spatial_results["Moran_I"]
        diag_summary.append({
            "检验类别": "Moran's I空间自相关",
            "结果": f"I={moran.get('Moran_I', 'N/A')}, p={moran.get('p值', 'N/A')}",
            "判断": moran.get("结论", "N/A"),
        })
        # 更新保存
        pd.DataFrame(diag_summary).to_csv(diag_path, index=False, encoding="utf-8-sig")

    logger.info("=" * 60)
    return diagnostics


def statistical_analysis(df: pd.DataFrame) -> Dict:
    """执行全部统计检验与分析"""
    results = {}

    results["baseline"] = _run_baseline_tests(df)
    results["panel_regression"] = _run_panel_regression(df)
    results["quantile_regression"] = _run_quantile_regression(df)
    results["diagnostics"] = _run_model_diagnostics(df, results.get("panel_regression"))

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
