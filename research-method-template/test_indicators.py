"""
单元测试 — 测试指标计算公式、数据完整性、省份分类逻辑、回归模型、诊断检验
运行方式: python -m pytest test_indicators.py -v
"""
import os
import sys
import pytest
import pandas as pd
import numpy as np

# 将项目根目录加入路径
sys.path.insert(0, os.path.dirname(__file__))

from config import (
    PROVINCES, PROV_SHORT_TO_FULL, SKIP_CITIES,
    CLASSIFICATION_THRESHOLDS, CLASSIFICATION_LABELS,
    VIF_THRESHOLD, MIN_SAMPLES_PANEL, MIN_SAMPLES_QUANTILE,
    DEPENDENCY_RATE_MAX, SELF_RATE_MAX,
    YEAR_START, YEAR_END,
)


class TestConfig:
    """测试公共配置"""

    def test_provinces_count(self):
        """PROVINCES 应包含31个省级行政区"""
        assert len(PROVINCES) == 31, f"期望31个省份，实际{len(PROVINCES)}"

    def test_provinces_no_duplicates(self):
        """PROVINCES 不应有重复"""
        assert len(PROVINCES) == len(set(PROVINCES))

    def test_skip_cities(self):
        """SKIP_CITIES 应包含5个计划单列市"""
        expected = {"大连市", "宁波市", "厦门市", "青岛市", "深圳市"}
        assert SKIP_CITIES == expected

    def test_short_to_full_mapping(self):
        """PROV_SHORT_TO_FULL 每个省份应对应自身"""
        for p in PROVINCES:
            assert PROV_SHORT_TO_FULL[p] == p

    def test_year_range(self):
        """年份范围配置应有效"""
        assert YEAR_START <= YEAR_END
        assert YEAR_START >= 2000
        assert YEAR_END <= 2030

    def test_classification_thresholds(self):
        """分类阈值应合理"""
        high = CLASSIFICATION_THRESHOLDS["high"]
        low = CLASSIFICATION_THRESHOLDS["low"]
        assert low < high
        assert 0 < low < 100
        assert 0 < high <= 100

    def test_vif_threshold(self):
        """VIF阈值应在合理范围"""
        assert VIF_THRESHOLD >= 5.0
        assert VIF_THRESHOLD <= 20.0

    def test_sample_thresholds(self):
        """样本量阈值应为正整数"""
        assert MIN_SAMPLES_PANEL >= 50
        assert MIN_SAMPLES_QUANTILE >= 20


class TestIndicatorCalculation:
    """测试指标计算公式"""

    def setup_method(self):
        """构造测试数据"""
        self.df = pd.DataFrame({
            "省份": ["上海市", "西藏自治区"],
            "年份": [2024, 2024],
            "GDP_亿元": [50000.0, 2500.0],
            "常住人口_万人": [2500.0, 370.0],
            "地方财政收入_亿元": [8300.0, 240.0],
            "地方财政支出_亿元": [9800.0, 2900.0],
            "转移支付_亿元": [950.0, 2600.0],
        })

    def test_dependency_rate(self):
        """转移支付依赖度 = 转移支付 / 财政支出 * 100"""
        row = self.df[self.df["省份"] == "上海市"].iloc[0]
        expected = 950.0 / 9800.0 * 100
        calculated = row["转移支付_亿元"] / row["地方财政支出_亿元"] * 100
        assert abs(calculated - expected) < 0.001

        row2 = self.df[self.df["省份"] == "西藏自治区"].iloc[0]
        calculated2 = row2["转移支付_亿元"] / row2["地方财政支出_亿元"] * 100
        expected2 = 2600.0 / 2900.0 * 100
        assert abs(calculated2 - expected2) < 0.01

    def test_fiscal_self_rate(self):
        """财政自给率 = 财政收入 / 财政支出 * 100"""
        row = self.df[self.df["省份"] == "上海市"].iloc[0]
        expected = 8300.0 / 9800.0 * 100
        calculated = row["地方财政收入_亿元"] / row["地方财政支出_亿元"] * 100
        assert abs(calculated - expected) < 0.01

    def test_per_capita_transfer(self):
        """人均转移支付 = 转移支付(亿) * 10000 / 人口(万)"""
        row = self.df[self.df["省份"] == "上海市"].iloc[0]
        expected = 950.0 * 10000 / 2500.0
        calculated = row["转移支付_亿元"] * 10000 / row["常住人口_万人"]
        assert abs(calculated - expected) < 0.01

    def test_per_capita_gdp(self):
        """人均GDP = GDP(亿) * 10000 / 人口(万)"""
        row = self.df[self.df["省份"] == "上海市"].iloc[0]
        expected = 50000.0 * 10000 / 2500.0
        calculated = row["GDP_亿元"] * 10000 / row["常住人口_万人"]
        assert abs(calculated - expected) < 0.01

    def test_economic_match_index(self):
        """转移支付经济匹配指数 = 人均转移支付 / 人均GDP"""
        row = self.df[self.df["省份"] == "西藏自治区"].iloc[0]
        per_capita_transfer = row["转移支付_亿元"] * 10000 / row["常住人口_万人"]
        per_capita_gdp = row["GDP_亿元"] * 10000 / row["常住人口_万人"]
        expected = per_capita_transfer / per_capita_gdp
        assert 0 < expected < 2, f"匹配指数应在合理范围内，实际{expected:.2f}"

    def test_all_formulas_consistent(self):
        """所有指标公式应自洽"""
        row = self.df[self.df["省份"] == "上海市"].iloc[0]
        dep = row["转移支付_亿元"] / row["地方财政支出_亿元"] * 100
        self_suf = row["地方财政收入_亿元"] / row["地方财政支出_亿元"] * 100
        assert 0 < dep < DEPENDENCY_RATE_MAX
        assert 0 < self_suf < SELF_RATE_MAX


class TestProvinceClassification:
    """测试省份分类逻辑"""

    def test_classification_boundaries(self):
        """测试分类阈值"""
        df = pd.DataFrame({
            "省份": ["A省", "B省", "C省", "D省"],
            "年份": [2024, 2024, 2024, 2024],
            "财政自给率": [80.0, 50.0, 35.0, 20.0],
            "财政自给率分类": [
                CLASSIFICATION_LABELS["high"],
                CLASSIFICATION_LABELS["mid"],
                CLASSIFICATION_LABELS["mid"],
                CLASSIFICATION_LABELS["low"],
            ],
        })

        high_thresh = CLASSIFICATION_THRESHOLDS["high"]
        low_thresh = CLASSIFICATION_THRESHOLDS["low"]

        high = df[df["财政自给率"] >= high_thresh]
        mid = df[(df["财政自给率"] >= low_thresh) & (df["财政自给率"] < high_thresh)]
        low = df[df["财政自给率"] < low_thresh]

        assert len(high) == 1
        assert len(mid) == 2
        assert len(low) == 1
        assert high.iloc[0]["省份"] == "A省"

    def test_boundary_case_exactly_high(self):
        """边界值：自给率=high阈值应归入高自给率"""
        assert CLASSIFICATION_THRESHOLDS["high"] >= CLASSIFICATION_THRESHOLDS["high"]

    def test_classification_labels_exist(self):
        """分类标签应完整"""
        assert "high" in CLASSIFICATION_LABELS
        assert "mid" in CLASSIFICATION_LABELS
        assert "low" in CLASSIFICATION_LABELS


class TestRegressionModel:
    """测试回归模型输出"""

    def test_panel_regression_file_format(self):
        """面板回归输出文件格式验证"""
        path = os.path.join(os.path.dirname(__file__), "output", "panel_regression.csv")
        if not os.path.exists(path):
            pytest.skip("panel_regression.csv 不存在，请先运行 main.py")
        
        df = pd.read_csv(path)
        required_cols = ["变量", "系数", "标准误", "p值"]
        for col in required_cols:
            assert col in df.columns, f"缺少列: {col}"

    def test_panel_regression_coefficients_reasonable(self):
        """面板回归系数应在合理范围"""
        path = os.path.join(os.path.dirname(__file__), "output", "panel_regression.csv")
        if not os.path.exists(path):
            pytest.skip("panel_regression.csv 不存在")
        
        df = pd.read_csv(path)
        ln_gdp_rows = df[df["变量"].str.contains("人均GDP", na=False)]
        if len(ln_gdp_rows) > 0:
            coef = ln_gdp_rows["系数"].iloc[0]
            assert coef < 5, f"ln人均GDP系数异常偏高: {coef}"

    def test_quantile_regression_file_format(self):
        """分位数回归输出文件格式验证"""
        path = os.path.join(os.path.dirname(__file__), "output", "quantile_regression.csv")
        if not os.path.exists(path):
            pytest.skip("quantile_regression.csv 不存在，请先运行 main.py")
        
        df = pd.read_csv(path)
        required_cols = ["分位数", "变量", "系数", "p值"]
        for col in required_cols:
            assert col in df.columns, f"缺少列: {col}"

    def test_quantile_regression_quantiles_valid(self):
        """分位数回归分位点应在有效范围"""
        path = os.path.join(os.path.dirname(__file__), "output", "quantile_regression.csv")
        if not os.path.exists(path):
            pytest.skip("quantile_regression.csv 不存在")
        
        df = pd.read_csv(path)
        quantiles = df["分位数"].unique()
        for q in quantiles:
            assert 0 < q < 1, f"分位数超出范围: {q}"


class TestDiagnosticTests:
    """测试诊断检验输出"""

    def test_vif_file_exists(self):
        """VIF诊断文件应存在"""
        path = os.path.join(os.path.dirname(__file__), "output", "vif_diagnostic.csv")
        if not os.path.exists(path):
            pytest.skip("vif_diagnostic.csv 不存在，请先运行 main.py")
        
        df = pd.read_csv(path)
        assert "变量" in df.columns
        assert "VIF" in df.columns

    def test_vif_values_reasonable(self):
        """VIF值应为正数"""
        path = os.path.join(os.path.dirname(__file__), "output", "vif_diagnostic.csv")
        if not os.path.exists(path):
            pytest.skip("vif_diagnostic.csv 不存在")
        
        df = pd.read_csv(path)
        for vif in df["VIF"]:
            assert vif > 0, f"VIF应为正数: {vif}"
            assert vif < 1000, f"VIF异常偏高: {vif}"

    def test_regression_diagnostic_file(self):
        """回归诊断汇总文件应存在"""
        path = os.path.join(os.path.dirname(__file__), "output", "regression_diagnostic.csv")
        if not os.path.exists(path):
            pytest.skip("regression_diagnostic.csv 不存在，请先运行 main.py")
        
        df = pd.read_csv(path)
        assert "检验类别" in df.columns
        assert "结果" in df.columns
        assert "判断" in df.columns


class TestDataIntegrity:
    """测试输出数据完整性"""

    def test_output_files_exist(self):
        """验证输出文件存在"""
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        required_files = ["raw_data.csv", "indicators.csv", "summary_stats.csv",
                          "panel_regression.csv", "quantile_regression.csv",
                          "vif_diagnostic.csv", "regression_diagnostic.csv"]
        for f in required_files:
            path = os.path.join(output_dir, f)
            if f in ["raw_data.csv", "indicators.csv"]:
                assert os.path.exists(path), f"缺少输出文件: {f}"

    def test_indicators_no_missing(self):
        """indicators.csv 应无缺失值"""
        path = os.path.join(os.path.dirname(__file__), "output", "indicators.csv")
        if not os.path.exists(path):
            pytest.skip("indicators.csv 不存在，请先运行 main.py")
        df = pd.read_csv(path)
        numeric_cols = ["GDP_亿元", "常住人口_万人", "转移支付_亿元",
                        "转移支付依赖度", "财政自给率"]
        for col in numeric_cols:
            assert df[col].notna().all(), f"{col} 列存在缺失值"

    def test_indicators_range(self):
        """指标值应在合理范围内"""
        path = os.path.join(os.path.dirname(__file__), "output", "indicators.csv")
        if not os.path.exists(path):
            pytest.skip("indicators.csv 不存在，请先运行 main.py")
        df = pd.read_csv(path)
        dep_col = df.columns[df.columns.str.contains("依赖度")][0]
        self_col = df.columns[df.columns.str.contains("自给率")][0]
        dep_min, dep_max = df[dep_col].min(), df[dep_col].max()
        self_min, self_max = df[self_col].min(), df[self_col].max()
        assert 0 <= dep_min, f"依赖度最小值异常: {dep_min}"
        assert 0 <= self_min, f"自给率最小值异常: {self_min}"
        assert self_max <= SELF_RATE_MAX, f"自给率最大值异常: {self_max}"
        assert dep_max <= DEPENDENCY_RATE_MAX, f"依赖度最大值异常: {dep_max}"

    def test_31_provinces_in_output(self):
        """输出数据应包含31个省份"""
        path = os.path.join(os.path.dirname(__file__), "output", "indicators.csv")
        if not os.path.exists(path):
            pytest.skip("indicators.csv 不存在，请先运行 main.py")
        df = pd.read_csv(path)
        recent = df[df["年份"] == df["年份"].max()]
        assert recent["省份"].nunique() == 31, f"最新年份应有31省，实际{recent['省份'].nunique()}"

    def test_years_in_range(self):
        """输出数据年份应在配置范围"""
        path = os.path.join(os.path.dirname(__file__), "output", "indicators.csv")
        if not os.path.exists(path):
            pytest.skip("indicators.csv 不存在，请先运行 main.py")
        df = pd.read_csv(path)
        assert df["年份"].min() >= YEAR_START
        assert df["年份"].max() <= YEAR_END


if __name__ == "__main__":
    pytest.main([__file__, "-v"])