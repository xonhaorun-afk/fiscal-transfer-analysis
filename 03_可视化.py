"""
可视化模块 — matplotlib 统计图表 + geopandas PNG 地图 + seaborn 热力图
无 JavaScript 依赖，输出全部为 PNG 图片
"""
import os, json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import geopandas as gpd
import seaborn as sns
from config import OUTPUT_DIR

os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False


# ============================================================
# 数据加载
# ============================================================
def _load_indicators():
    path = os.path.join(OUTPUT_DIR, "indicators.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到指标数据: {path}。请先运行 02_数据处理.py")
    df = pd.read_csv(path)
    df["年份"] = df["年份"].astype(int)
    print(f"加载指标数据: {len(df)} 条记录")
    return df


def _load_geodataframe():
    geojson_path = os.path.join(OUTPUT_DIR, "china_provinces.geojson")
    gdf = gpd.read_file(geojson_path)
    gdf = gdf[gdf["name"] != ""]
    return gdf


# ============================================================
# PNG 地图（geopandas）
# ============================================================
def _choropleth_map(gdf, df, value_col, title, cmap, vmin, vmax,
                    cbar_label, filename, fmt="{z:.1f}"):
    """通用 choropleth 绘图"""
    year = int(df["年份"].max())
    recent = df[df["年份"] == year]
    gdf_plot = gdf.merge(recent, left_on="name", right_on="省份", how="left")

    fig, ax = plt.subplots(figsize=(12, 7))

    gdf_plot.plot(
        column=value_col, ax=ax, cmap=cmap, vmin=vmin, vmax=vmax,
        edgecolor="white", linewidth=0.5,
        legend=True,
        legend_kwds={"label": cbar_label, "shrink": 0.5, "pad": 0.02},
        missing_kwds={"color": "#e0e0e0"},
    )

    for _, row in gdf_plot.iterrows():
        if row.geometry is not None and pd.notna(row[value_col]):
            c = row.geometry.centroid
            ax.annotate(f"{row['省份']}\n{fmt.format(z=row[value_col])}",
                       (c.x, c.y), ha="center", va="center",
                       fontsize=5.5, color="#1a1a1a", fontweight="bold")

    ax.set_title(title, fontsize=14, fontweight="bold", pad=6)
    ax.axis("off")
    ax.set_xlim(73, 136)
    ax.set_ylim(16, 55)

    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.1, facecolor="white")
    plt.close(fig)
    print(f"  [OK] {path}")


def make_map_transfer_dependency(gdf, df):
    _choropleth_map(gdf, df, "转移支付依赖度",
                    title=f"各省中央转移支付依赖度（{df['年份'].max()}年）",
                    cmap="OrRd", vmin=0, vmax=90,
                    cbar_label="转移支付依赖度（%）",
                    filename="地图_转移支付依赖度.png")


def make_map_per_capita(gdf, df):
    _choropleth_map(gdf, df, "人均转移支付_元",
                    title=f"各省人均转移支付（{df['年份'].max()}年）",
                    cmap="Blues", vmin=2000, vmax=25000,
                    cbar_label="人均转移支付（元/人）",
                    filename="地图_人均转移支付.png",
                    fmt="{z:,.0f}")


def make_map_fiscal_self(gdf, df):
    _choropleth_map(gdf, df, "财政自给率",
                    title=f"各省财政自给率（{df['年份'].max()}年）",
                    cmap="RdYlGn", vmin=0, vmax=100,
                    cbar_label="财政自给率（%）",
                    filename="地图_财政自给率.png")


def make_map_timeline(gdf, df):
    """逐年变化量地图（2019-2024，RdBu 双色）"""
    df_sorted = df.sort_values(["省份", "年份"])
    df_sorted["变化量"] = df_sorted.groupby("省份")["转移支付依赖度"].diff()
    change = df_sorted[df_sorted["变化量"].notna()].copy()
    years = sorted(change["年份"].unique())

    vmax = max(abs(change["变化量"].min()), abs(change["变化量"].max()))
    vmax = np.ceil(vmax / 5) * 5

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    for i, year in enumerate(years):
        ax = axes.flat[i]
        recent = change[change["年份"] == year]
        gdf_plot = gdf.merge(recent, left_on="name", right_on="省份", how="left")
        gdf_plot.plot(
            column="变化量", ax=ax, cmap="RdBu_r", vmin=-vmax, vmax=vmax,
            edgecolor="white", linewidth=0.3,
            legend=True,
            legend_kwds={"label": "较上年变化（百分点）", "shrink": 0.5, "pad": 0.02},
            missing_kwds={"color": "#e0e0e0"},
        )
        for _, row in gdf_plot.iterrows():
            if row.geometry is not None and pd.notna(row["变化量"]):
                c = row.geometry.centroid
                val = row["变化量"]
                sign = "+" if val >= 0 else ""
                ax.annotate(f"{row['省份']}\n{sign}{val:.1f}%", (c.x, c.y),
                           ha="center", va="center", fontsize=5.5,
                           color="#1a1a1a", fontweight="bold")
        ax.set_title(f"{year-1}→{year}年", fontsize=12, fontweight="bold", pad=2)
        ax.axis("off")
        ax.set_xlim(73, 136); ax.set_ylim(16, 55)

    fig.suptitle("各省转移支付依赖度较上年变化\n红色=依赖度上升，蓝色=依赖度下降",
                 fontsize=16, fontweight="bold", y=1.01)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "地图_转移支付依赖度_时序.png")
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.1, facecolor="white")
    plt.close(fig)
    print(f"  [OK] {path}")


def make_map_dashboard(gdf, df):
    """综合仪表盘：双图并排"""
    year = int(df["年份"].max())
    recent = df[df["年份"] == year]
    gdf_plot = gdf.merge(recent, left_on="name", right_on="省份", how="left")

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))

    gdf_plot.plot(column="转移支付依赖度", ax=axes[0], cmap="OrRd",
                  vmin=0, vmax=90, edgecolor="white", linewidth=0.4,
                  legend=True, legend_kwds={"label": "依赖度（%）", "shrink": 0.5, "pad": 0.02},
                  missing_kwds={"color": "#e0e0e0"})
    axes[0].set_title("转移支付依赖度（%）", fontsize=13, fontweight="bold", pad=4)
    axes[0].axis("off"); axes[0].set_xlim(73, 136); axes[0].set_ylim(16, 55)

    gdf_plot.plot(column="财政自给率", ax=axes[1], cmap="RdYlGn",
                  vmin=0, vmax=100, edgecolor="white", linewidth=0.4,
                  legend=True, legend_kwds={"label": "自给率（%）", "shrink": 0.5, "pad": 0.02},
                  missing_kwds={"color": "#e0e0e0"})
    axes[1].set_title("财政自给率（%）", fontsize=13, fontweight="bold", pad=4)
    axes[1].axis("off"); axes[1].set_xlim(73, 136); axes[1].set_ylim(16, 55)

    fig.suptitle(f"中央—地方财政转移支付综合分析仪表盘（{year}年）",
                 fontsize=16, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "仪表盘_综合.png")
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.1, facecolor="white")
    plt.close(fig)
    print(f"  [OK] {path}")


# ============================================================
# 统计图表（matplotlib）
# ============================================================
def make_stat_ranking(df):
    """财政自给率排名（横向柱状图）"""
    recent = df[df["年份"] == df["年份"].max()].sort_values("财政自给率", ascending=True)
    fig, ax = plt.subplots(figsize=(12, 10))
    colors = ["#c23531" if v < 35 else "#f4a742" if v < 60 else "#61a0a8"
              for v in recent["财政自给率"]]
    bars = ax.barh(recent["省份"], recent["财政自给率"], color=colors, edgecolor="white")
    for bar, val in zip(bars, recent["财政自给率"]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=8)
    ax.axvline(x=50, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("财政自给率（%）", fontsize=12)
    ax.set_title(f"各省财政自给率排名（{df['年份'].max()}年）", fontsize=14, fontweight="bold")
    ax.set_xlim(0, recent["财政自给率"].max() * 1.15)
    ax.legend(handles=[
        Patch(facecolor="#c23531", label="低自给率（<35%）"),
        Patch(facecolor="#f4a742", label="中自给率（35%-60%）"),
        Patch(facecolor="#61a0a8", label="高自给率（≥60%）"),
    ], loc="lower right")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "统计图_财政自给率排名.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


def make_stat_scatter(df):
    """转移支付 vs GDP 散点图"""
    recent = df[df["年份"] == df["年份"].max()]
    fig, ax = plt.subplots(figsize=(10, 8))
    scatter = ax.scatter(
        recent["人均GDP_元"], recent["人均转移支付_元"],
        c=recent["财政自给率"], cmap="RdYlGn",
        s=recent["常住人口_万人"] / 50, alpha=0.7,
        edgecolors="gray", linewidth=0.5,
    )
    for _, row in recent.iterrows():
        if row["人均转移支付_元"] > 15000 or row["人均GDP_元"] > 100000:
            ax.annotate(row["省份"], (row["人均GDP_元"], row["人均转移支付_元"]),
                       fontsize=8, xytext=(5, 5), textcoords="offset points")
    ax.set_xlabel("人均GDP（元）", fontsize=12)
    ax.set_ylabel("人均转移支付（元）", fontsize=12)
    ax.set_title(f"转移支付与经济发展水平（{df['年份'].max()}年）", fontsize=14, fontweight="bold")
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("财政自给率（%）", fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "统计图_转移支付vs人均GDP.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


def make_stat_category(df):
    """三类省份对比（分组柱状图）"""
    recent = df[df["年份"] == df["年份"].max()]
    categories = ["高自给率（≥60%）", "中自给率（35%-60%）", "低自给率（<35%）"]
    metrics = ["转移支付依赖度", "人均转移支付_元", "人均GDP_元"]
    labels = ["转移支付依赖度（%）", "人均转移支付（元）", "人均GDP（元）"]
    group_means = recent.groupby("财政自给率分类")[metrics].mean()
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    colors = ["#61a0a8", "#f4a742", "#c23531"]
    for ax, metric, label in zip(axes, metrics, labels):
        values = [group_means.loc[c, metric] if c in group_means.index else 0
                  for c in categories]
        bars = ax.bar(categories, values, color=colors, edgecolor="white")
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                    f"{val:.0f}", ha="center", fontsize=11, fontweight="bold")
        ax.set_title(label, fontsize=13, fontweight="bold")
        ax.tick_params(axis="x", rotation=10, labelsize=9)
    fig.suptitle(f"三类财政自给率省份的关键指标对比（{df['年份'].max()}年）",
                 fontsize=15, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "统计图_三类省份对比.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


def make_stat_trend(df):
    """全国趋势折线图"""
    yearly = df.groupby("年份").agg(
        平均转移支付依赖度=("转移支付依赖度", "mean"),
        平均财政自给率=("财政自给率", "mean"),
        转移支付总额_万亿=("转移支付_亿元", lambda x: x.sum() / 10000),
    ).reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    ax.plot(yearly["年份"], yearly["平均转移支付依赖度"], "o-", color="#c23531",
            linewidth=2, markersize=6, label="平均转移支付依赖度（%）")
    ax.plot(yearly["年份"], yearly["平均财政自给率"], "s-", color="#2f4554",
            linewidth=2, markersize=6, label="平均财政自给率（%）")
    ax.set_xlabel("年份"); ax.set_title("全国平均财政指标趋势", fontweight="bold")
    ax.legend(); ax.grid(True, alpha=0.3); ax.set_xticks(yearly["年份"])

    ax = axes[1]
    ax.fill_between(yearly["年份"], yearly["转移支付总额_万亿"], alpha=0.3, color="#61a0a8")
    ax.plot(yearly["年份"], yearly["转移支付总额_万亿"], "o-", color="#2f4554",
            linewidth=2, markersize=6)
    ax.set_xlabel("年份"); ax.set_ylabel("万亿元")
    ax.set_title("中央对地方转移支付总额", fontweight="bold")
    ax.grid(True, alpha=0.3); ax.set_xticks(yearly["年份"])

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "统计图_全国趋势.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {path}")


# ============================================================
# seaborn 相关性热力图
# ============================================================
def make_stat_correlation_heatmap(df):
    """指标间Pearson相关系数热力图"""
    recent = df[df["年份"] == df["年份"].max()]
    metric_labels = {
        "转移支付依赖度": "转移支付\n依赖度",
        "人均转移支付_元": "人均\n转移支付",
        "财政自给率": "财政\n自给率",
        "人均GDP_元": "人均\nGDP",
        "转移支付经济匹配指数": "经济\n匹配指数",
    }
    numeric_cols = list(metric_labels.keys())
    corr = recent[numeric_cols].corr()

    # 重命名列/行为简短标签
    short_labels = [metric_labels[c] for c in numeric_cols]
    corr.index = short_labels
    corr.columns = short_labels

    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)  # 只显示下三角
    sns.heatmap(
        corr, annot=True, fmt=".3f", cmap="RdBu_r",
        vmin=-1, vmax=1, center=0,
        mask=mask, square=True,
        linewidths=0.5, linecolor="white",
        cbar_kws={"label": "Pearson r", "shrink": 0.8},
        ax=ax,
        annot_kws={"fontsize": 12, "fontweight": "bold"},
    )
    ax.set_title(
        f"核心指标 Pearson 相关系数矩阵（{df['年份'].max()}年）",
        fontsize=14, fontweight="bold", pad=12,
    )
    ax.tick_params(labelsize=10)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "统计图_相关性热力图.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [OK] {path}")


# ============================================================
# 主入口
# ============================================================
def visualize_all():
    print("=" * 60)
    print("数据可视化")
    print("=" * 60)

    df = _load_indicators()
    gdf = _load_geodataframe()

    print("\n>>> PNG 地图（geopandas）")
    make_map_transfer_dependency(gdf, df)
    make_map_per_capita(gdf, df)
    make_map_fiscal_self(gdf, df)
    make_map_timeline(gdf, df)
    make_map_dashboard(gdf, df)

    print("\n>>> 统计图表（matplotlib）")
    make_stat_ranking(df)
    make_stat_scatter(df)
    make_stat_category(df)
    make_stat_trend(df)

    print("\n>>> 相关性热力图（seaborn）")
    make_stat_correlation_heatmap(df)

    print("\n" + "=" * 60)
    print(f"全部图表已保存至: {OUTPUT_DIR}")
    print("=" * 60)


# ============================================================
# 交互式仪表盘
# ============================================================
def build_dashboard():
    """将 indicators.csv 嵌入仪表盘 HTML 模板，生成自包含的交互式仪表盘"""
    import csv

    csv_path = os.path.join(OUTPUT_DIR, "indicators.csv")
    template_path = os.path.join(OUTPUT_DIR, "..", "dashboard_template.html")
    template_path = os.path.abspath(template_path)
    output_path = os.path.join(OUTPUT_DIR, "dashboard.html")

    if not os.path.exists(csv_path):
        print("  请先运行 main.py 生成 indicators.csv")
        return
    if not os.path.exists(template_path):
        print(f"  模板文件不存在: {template_path}")
        return

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = [row for row in csv.DictReader(f)]

    # ensure_ascii=True → 纯 ASCII 输出，任何浏览器兼容
    data_json = json.dumps(rows, ensure_ascii=True)

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("__DATA_PLACEHOLDER__", data_json)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  [OK] 交互式仪表盘: {output_path} ({len(rows)} 条记录)")


if __name__ == "__main__":
    visualize_all()
