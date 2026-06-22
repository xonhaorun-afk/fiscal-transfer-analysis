"""
中央—地方财政转移支付效果分析
多源部委数据综合大作业 — 主入口

用法:
    python main.py              # 执行全部流程
    python main.py --collect    # 仅数据采集
    python main.py --process    # 仅数据处理
    python main.py --visualize  # 仅可视化
    python main.py --dashboard  # 仅构建交互式仪表盘
"""
import sys
import os

BASE_DIR = os.path.dirname(__file__)
os.chdir(BASE_DIR)


def main():
    args = sys.argv[1:]

    run_all = len(args) == 0
    run_collect = run_all or "--collect" in args
    run_process = run_all or "--process" in args
    run_visualize = run_all or "--visualize" in args
    run_dashboard = run_all or "--dashboard" in args

    print("=" * 60)
    print("  中央—地方财政转移支付效果分析")
    print("  人工智能与计算思维 · 2026春季学期大作业")
    print("=" * 60)

    # Step 1: 数据采集
    if run_collect:
        import importlib
        collect_all = importlib.import_module("01_数据采集").collect_all
        collect_all()

    # Step 2: 数据处理与指标计算
    if run_process:
        import importlib
        process_all = importlib.import_module("02_数据处理").process_all
        process_all()

    # Step 3: 数据可视化
    if run_visualize:
        import importlib
        visualize_all = importlib.import_module("03_可视化").visualize_all
        visualize_all()

    # Step 4: 构建交互式仪表盘
    if run_dashboard:
        import importlib
        build_dashboard = importlib.import_module("03_可视化").build_dashboard
        build_dashboard()

    print("\n" + "=" * 60)
    print("  全流程完成！输出文件位于 output/ 目录")
    print("  双击 output/dashboard.html 打开交互式仪表盘")
    print("=" * 60)


if __name__ == "__main__":
    main()
