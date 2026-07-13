"""
数据采集模块 — 三级降级策略
  模式A（真实数据）: 从 数据/ 目录读取 EPS 平台 + 财政部决算 Excel
  模式B（在线采集）: 尝试 akshare + 国家统计局 API 获取省级面板数据
  模式C（估算备用）: 内置基准值 + 增速回推，保证程序可运行

用法:
    python 01_数据采集.py           # 自动选择可用模式（A > B > C）
    python 01_数据采集.py --real    # 强制真实数据模式
    python 01_数据采集.py --online  # 强制在线采集模式
    python 01_数据采集.py --fallback # 强制 fallback 估算模式
"""
import os
import sys
import logging
from typing import Optional, Dict, List
import pandas as pd
import numpy as np
from config import (
    BASE_DIR, OUTPUT_DIR, DATA_DIR,
    PROVINCES, PROV_SHORT_TO_FULL, SKIP_CITIES,
    YEAR_START, YEAR_END,
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================
# 模式A: 解析真实 Excel 数据
# ============================================================
def _parse_eps_file(filepath: str, value_name: str) -> pd.DataFrame:
    """
    解析 EPS 数据平台导出的 Excel（4行头 + 省份数据行）
    自动检测数据行范围，不再硬编码行号
    """
    df_raw = pd.read_excel(filepath, header=None)
    rows = []
    start_row = None
    year_row_count = 0

    for i in range(len(df_raw)):
        cell_val = str(df_raw.iloc[i, 0]).strip()
        if cell_val in PROV_SHORT_TO_FULL:
            if start_row is None:
                start_row = i
            year_row_count += 1

    if start_row is None:
        logger.warning(f"  在 {os.path.basename(filepath)} 中未找到省份数据，尝试回退到第4行")
        start_row = 4
        year_row_count = 31

    end_row = start_row + year_row_count
    for i in range(start_row, end_row):
        if i >= len(df_raw):
            break
        province = str(df_raw.iloc[i, 0]).strip()
        if province not in PROV_SHORT_TO_FULL:
            continue
        full = PROV_SHORT_TO_FULL[province]
        for j in range(1, 8):
            if j >= df_raw.shape[1]:
                break
            year = YEAR_END - (j - 1)
            if year < YEAR_START or year > YEAR_END:
                continue
            val = df_raw.iloc[i, j]
            rows.append({
                "省份": full,
                "年份": year,
                value_name: pd.to_numeric(val, errors="coerce"),
            })
    return pd.DataFrame(rows)


def _parse_transfer_files() -> pd.DataFrame:
    """解析财政部转移支付决算 Excel（按年份分文件）"""
    rows: List[Dict] = []
    for year in range(YEAR_START, YEAR_END + 1):
        fpath = os.path.join(DATA_DIR, "转移支付", f"{year}.xlsx")
        if not os.path.exists(fpath):
            continue
        df = pd.read_excel(fpath, header=None)
        for i in range(len(df)):
            name = str(df.iloc[i, 0]).strip().replace("\xa0", "")
            if not name or name == "nan" or name in SKIP_CITIES:
                continue
            if name in {"合计", "总计"} or len(name) < 2:
                continue
            if name not in PROV_SHORT_TO_FULL:
                base = name.split("（")[0].split("(")[0]
                if base in PROV_SHORT_TO_FULL:
                    name = base
                else:
                    continue
            val = pd.to_numeric(df.iloc[i, 2], errors="coerce") if df.shape[1] > 2 else np.nan
            if pd.isna(val) and df.shape[1] > 1:
                val = pd.to_numeric(df.iloc[i, 1], errors="coerce")
            rows.append({
                "省份": PROV_SHORT_TO_FULL[name],
                "年份": year,
                "转移支付_亿元": val,
            })
    return pd.DataFrame(rows)


def collect_real() -> pd.DataFrame:
    """加载真实 Excel 数据并合并"""
    logger.info("=" * 50)
    logger.info("  模式A: 加载真实 Excel 数据")
    logger.info("=" * 50)

    df_gdp = _parse_eps_file(os.path.join(DATA_DIR, "2018-2024各省gdp.xlsx"), "GDP_亿元")
    logger.info(f"  GDP: {len(df_gdp)} 条, {df_gdp['省份'].nunique()} 省")

    df_pop = _parse_eps_file(os.path.join(DATA_DIR, "2018-2024各省人口.xlsx"), "常住人口_万人")
    logger.info(f"  人口: {len(df_pop)} 条, {df_pop['省份'].nunique()} 省")

    df_rev = _parse_eps_file(
        os.path.join(DATA_DIR, "2018-2024地方财政一般公共预算收入.xlsx"),
        "地方财政收入_亿元",
    )
    logger.info(f"  财政收入: {len(df_rev)} 条, {df_rev['省份'].nunique()} 省")

    df_exp = _parse_eps_file(
        os.path.join(DATA_DIR, "2018-2024各省地方一般公共预算支出.xlsx"),
        "地方财政支出_亿元",
    )
    logger.info(f"  财政支出: {len(df_exp)} 条, {df_exp['省份'].nunique()} 省")

    df_trans = _parse_transfer_files()
    logger.info(f"  转移支付: {len(df_trans)} 条, {df_trans['省份'].nunique()} 省")

    merged = (
        df_gdp.merge(df_pop, on=["省份", "年份"], how="outer")
        .merge(df_rev, on=["省份", "年份"], how="outer")
        .merge(df_exp, on=["省份", "年份"], how="outer")
        .merge(df_trans, on=["省份", "年份"], how="outer")
    )
    merged = merged.drop_duplicates(subset=["省份", "年份"]).sort_values(["省份", "年份"])
    return merged


# ============================================================
# 模式B: 在线采集（akshare + 国家统计局）
# ============================================================
def _normalize_province(name: str) -> str:
    if not isinstance(name, str):
        return name
    name = name.strip().replace("省", "").replace("市", "").replace("自治区", "")
    name = name.replace("壮族", "").replace("回族", "").replace("维吾尔", "")
    mapping = {
        "北京": "北京市", "天津": "天津市", "上海": "上海市", "重庆": "重庆市",
        "河北": "河北省", "山西": "山西省", "内蒙古": "内蒙古自治区",
        "辽宁": "辽宁省", "吉林": "吉林省", "黑龙江": "黑龙江省",
        "江苏": "江苏省", "浙江": "浙江省", "安徽": "安徽省",
        "福建": "福建省", "江西": "江西省", "山东": "山东省",
        "河南": "河南省", "湖北": "湖北省", "湖南": "湖南省",
        "广东": "广东省", "广西": "广西壮族自治区", "海南": "海南省",
        "四川": "四川省", "贵州": "贵州省", "云南": "云南省",
        "西藏": "西藏自治区", "陕西": "陕西省", "甘肃": "甘肃省",
        "青海": "青海省", "宁夏": "宁夏回族自治区", "新疆": "新疆维吾尔自治区",
    }
    return mapping.get(name, name)


def _try_akshare_collect() -> Optional[pd.DataFrame]:
    """
    尝试使用 akshare 的国家统计局接口采集省级面板数据
    成功返回 DataFrame，失败返回 None
    """
    try:
        import akshare as ak
    except ImportError:
        logger.warning("  akshare 未安装，跳过在线采集")
        return None

    logger.info("  尝试 akshare 在线采集...")

    indicators = {
        "GDP_亿元": "A020101",
        "常住人口_万人": "A030101",
        "地方财政收入_亿元": "A090101",
        "地方财政支出_亿元": "A090201",
    }

    collected: Dict[str, pd.DataFrame] = {}
    success_count = 0

    for col_name, indicator_code in indicators.items():
        try:
            df = ak.macro_china_nbs_region(kind="年度数据", path="分省年度数据", indicator=indicator_code)
            if df is None or df.empty:
                logger.warning(f"    {col_name} ({indicator_code}): 返回空数据")
                continue

            if "地区" not in df.columns:
                logger.warning(f"    {col_name}: 未找到'地区'列，列名={df.columns.tolist()[:5]}")
                continue

            records = []
            for _, row in df.iterrows():
                prov = _normalize_province(str(row["地区"]))
                if prov not in PROVINCES:
                    continue
                for col in df.columns:
                    if col == "地区":
                        continue
                    year_str = str(col).replace("年", "").strip()
                    try:
                        year = int(year_str)
                    except (ValueError, TypeError):
                        continue
                    if year < YEAR_START or year > YEAR_END:
                        continue
                    val = pd.to_numeric(row[col], errors="coerce")
                    if pd.notna(val):
                        records.append({"省份": prov, "年份": year, col_name: val})

            if records:
                collected[col_name] = pd.DataFrame(records)
                success_count += 1
                logger.info(f"    {col_name}: 采集到 {len(records)} 条")
            else:
                logger.warning(f"    {col_name}: 无有效记录")
        except Exception as e:
            logger.warning(f"    {col_name} ({indicator_code}) 采集失败: {e}")

    if success_count < 2:
        logger.warning("  akshare 采集成功率过低，降级到 fallback")
        return None

    merged = None
    for col_name, df_part in collected.items():
        if merged is None:
            merged = df_part
        else:
            merged = merged.merge(df_part, on=["省份", "年份"], how="outer")

    if merged is None:
        return None

    logger.info(f"  akshare 采集完成: {len(merged)} 条记录, {merged['省份'].nunique()} 省")
    return merged


# ============================================================
# 模式C: Fallback 估算数据
# ============================================================
def _fallback_data(base_dict: Dict[str, float], value_col: str,
                   base_year: int = 2023, rate: float = 0.06) -> pd.DataFrame:
    """通用 fallback：以 base_year 为基准按年增速回推"""
    records = []
    for yr in range(YEAR_START, YEAR_END + 1):
        for prov in PROVINCES:
            val = base_dict.get(prov, 5000) / ((1 + rate) ** (base_year - yr))
            records.append({"省份": prov, "年份": yr, value_col: round(val, 1)})
    return pd.DataFrame(records)


def _fallback_collect() -> pd.DataFrame:
    """
    使用内置基准值 + 固定增速生成估算数据
    基准值参考：国家统计局2023年公开数据
    """
    logger.warning("=" * 50)
    logger.warning("  模式C: 使用内置估算数据（Fallback）")
    logger.warning("  数据为估算值，仅供测试程序流程使用")
    logger.warning("=" * 50)

    gdp_2023 = {
        "广东省": 135673, "江苏省": 128222, "山东省": 92069, "浙江省": 82553,
        "河南省": 59132, "四川省": 60133, "湖北省": 55803, "福建省": 54355,
        "湖南省": 50012, "安徽省": 47050, "上海市": 47219, "河北省": 43944,
        "北京市": 43760, "陕西省": 33786, "江西省": 32200, "辽宁省": 30209,
        "重庆市": 30146, "云南省": 30021, "广西壮族自治区": 27202, "山西省": 25698,
        "内蒙古自治区": 24627, "贵州省": 20913, "新疆维吾尔自治区": 19126,
        "天津市": 16737, "黑龙江省": 15884, "吉林省": 13531, "甘肃省": 11864,
        "海南省": 7551, "宁夏回族自治区": 5315, "青海省": 3799, "西藏自治区": 2393,
    }
    pop_2023 = {
        "广东省": 12706, "山东省": 10123, "河南省": 9815, "江苏省": 8526,
        "四川省": 8368, "河北省": 7420, "湖南省": 6568, "浙江省": 6627,
        "安徽省": 6121, "湖北省": 5838, "广西壮族自治区": 5043, "云南省": 4673,
        "江西省": 4515, "辽宁省": 4182, "福建省": 4183, "陕西省": 3956,
        "贵州省": 3865, "山西省": 3466, "重庆市": 3191, "黑龙江省": 3062,
        "新疆维吾尔自治区": 2598, "甘肃省": 2465, "吉林省": 2348, "内蒙古自治区": 2396,
        "上海市": 2487, "北京市": 2188, "天津市": 1364, "海南省": 1043,
        "宁夏回族自治区": 729, "青海省": 594, "西藏自治区": 366,
    }
    rev_2023 = {
        "广东省": 13900, "江苏省": 9930, "浙江省": 8600, "上海市": 8372,
        "山东省": 7465, "北京市": 6181, "四川省": 5529, "河南省": 4518,
        "河北省": 4286, "安徽省": 3939, "福建省": 3920, "湖北省": 3690,
        "湖南省": 3360, "江西省": 3075, "山西省": 3450, "辽宁省": 2905,
        "陕西省": 2901, "内蒙古自治区": 3084, "重庆市": 2441, "云南省": 2223,
        "贵州省": 2078, "天津市": 2042, "新疆维吾尔自治区": 1967, "广西壮族自治区": 1900,
        "黑龙江省": 1366, "吉林省": 1119, "甘肃省": 1002, "海南省": 921,
        "宁夏回族自治区": 502, "青海省": 385, "西藏自治区": 238,
    }
    exp_2023 = {
        "广东省": 18500, "江苏省": 15200, "山东省": 12500, "四川省": 12800,
        "河南省": 11000, "浙江省": 12300, "河北省": 9600, "湖南省": 9600,
        "湖北省": 9800, "安徽省": 8600, "上海市": 9800, "北京市": 8100,
        "江西省": 7500, "辽宁省": 6500, "福建省": 6800, "陕西省": 6800,
        "云南省": 6800, "广西壮族自治区": 6100, "贵州省": 5800, "山西省": 5800,
        "内蒙古自治区": 5800, "重庆市": 5300, "新疆维吾尔自治区": 5500,
        "黑龙江省": 5400, "吉林省": 4200, "甘肃省": 4500, "海南省": 2300,
        "天津市": 3400, "宁夏回族自治区": 1700, "青海省": 2100, "西藏自治区": 2800,
    }
    transfer_2023 = {
        "四川省": 6200, "河南省": 5500, "湖南省": 4300, "湖北省": 4200,
        "河北省": 3900, "云南省": 4200, "安徽省": 3800, "广西壮族自治区": 3800,
        "贵州省": 3700, "黑龙江省": 3700, "新疆维吾尔自治区": 3600, "江西省": 3500,
        "山东省": 3400, "甘肃省": 3200, "陕西省": 3100, "内蒙古自治区": 3000,
        "吉林省": 2900, "辽宁省": 2700, "山西省": 2500, "西藏自治区": 2600,
        "重庆市": 2100, "青海省": 1800, "宁夏回族自治区": 1200, "海南省": 1000,
        "广东省": 2200, "江苏省": 2100, "浙江省": 1800, "福建省": 1600,
        "北京市": 1100, "上海市": 1000, "天津市": 800,
    }

    merged = _fallback_data(gdp_2023, "GDP_亿元")
    merged = merged.merge(_fallback_data(pop_2023, "常住人口_万人", rate=0.002), on=["省份", "年份"])
    merged = merged.merge(_fallback_data(rev_2023, "地方财政收入_亿元", rate=0.05), on=["省份", "年份"])
    merged = merged.merge(_fallback_data(exp_2023, "地方财政支出_亿元"), on=["省份", "年份"])
    merged = merged.merge(_fallback_data(transfer_2023, "转移支付_亿元", rate=0.08), on=["省份", "年份"])
    return merged


# ============================================================
# 主入口
# ============================================================
def collect_all(mode: str = "auto") -> pd.DataFrame:
    """
    采集所有数据并保存 raw_data.csv

    Parameters
    ----------
    mode : str
        "auto" = 自动降级（real > online > fallback）
        "real" = 强制真实数据模式
        "online" = 强制在线采集模式
        "fallback" = 强制 fallback 估算模式
    """
    merged = None
    data_source = ""

    if mode in ("auto", "real"):
        gdp_file = os.path.join(DATA_DIR, "2018-2024各省gdp.xlsx")
        if os.path.exists(gdp_file):
            try:
                merged = collect_real()
                data_source = "real"
            except Exception as e:
                logger.error(f"  真实数据加载失败: {e}")
                if mode == "real":
                    raise

    if merged is None and mode in ("auto", "online"):
        logger.info("=" * 50)
        logger.info("  模式B: 在线采集（akshare 国家统计局接口）")
        logger.info("=" * 50)
        merged = _try_akshare_collect()
        if merged is not None:
            data_source = "online"

    if merged is None:
        merged = _fallback_collect()
        data_source = "fallback"

    merged = merged.sort_values(["省份", "年份"]).reset_index(drop=True)

    output_path = os.path.join(OUTPUT_DIR, "raw_data.csv")
    merged.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"\n原始数据已保存: {output_path}")
    logger.info(f"数据来源: {data_source}")
    logger.info(f"共 {len(merged)} 条记录, {merged['省份'].nunique()} 省, "
                f"{merged['年份'].min()}-{merged['年份'].max()} 年")
    return merged


if __name__ == "__main__":
    mode = "auto"
    if "--real" in sys.argv:
        mode = "real"
    elif "--online" in sys.argv:
        mode = "online"
    elif "--fallback" in sys.argv:
        mode = "fallback"
    collect_all(mode)
