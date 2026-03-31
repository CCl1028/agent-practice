"""基金投资助手 — 主入口

用法：
  python main.py                              # 运行每日简报
  python main.py add --screenshot photo.jpg   # 截图识别录入
  python main.py add --text "我买了2万易方达"   # 自然语言录入
"""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_daily_briefing() -> None:
    """运行每日简报流程。"""
    from src.graph import app
    from src.formatter import format_all

    logger.info("🚀 启动每日简报生成...")

    result = app.invoke({"trigger": "daily_briefing"})

    briefing = result.get("briefing")
    if not briefing:
        logger.error("❌ 未生成简报，请检查 Agent 日志")
        sys.exit(1)

    print("\n" + "=" * 50)
    print(format_all(briefing))
    print("=" * 50)

    if result.get("error"):
        logger.warning("⚠️  过程中有错误: %s", result["error"])

    logger.info("✅ 简报生成完成")


def run_add_from_screenshot(image_path: str) -> None:
    """截图识别录入持仓。"""
    from src.tools.ocr_tools import process_screenshot
    from src.tools.portfolio_tools import load_portfolio, save_portfolio
    from src.graph import app
    from src.formatter import format_all

    logger.info("📸 开始处理截图: %s", image_path)

    holdings = process_screenshot(image_path)
    if not holdings:
        logger.error("❌ 未识别到持仓信息，请检查截图")
        sys.exit(1)

    print("\n📋 识别到以下持仓：")
    for i, h in enumerate(holdings, 1):
        print(f"  {i}. {h['fund_name']}({h['fund_code']}) "
              f"金额:{h['cost']} 收益率:{h['profit_ratio']}%")

    # 合并保存
    existing = load_portfolio()
    existing_map = {f["fund_code"]: f for f in existing if f.get("fund_code")}
    for h in holdings:
        if h.get("fund_code"):
            existing_map[h["fund_code"]] = h
    merged = list(existing_map.values())
    save_portfolio(merged)
    logger.info("💾 已保存 %d 只基金持仓", len(merged))

    # 自动触发一次简报
    print("\n🚀 自动生成首次建议...")
    result = app.invoke({"trigger": "daily_briefing"})
    briefing = result.get("briefing")
    if briefing:
        print("\n" + "=" * 50)
        print(format_all(briefing))
        print("=" * 50)


def run_add_from_text(text: str) -> None:
    """自然语言录入持仓。"""
    from src.tools.nlp_input import parse_natural_language
    from src.tools.portfolio_tools import load_portfolio, save_portfolio
    from src.graph import app
    from src.formatter import format_all

    logger.info("💬 解析自然语言: %s", text)

    holdings = parse_natural_language(text)
    if not holdings:
        logger.error("❌ 未解析到持仓信息，请换个描述试试")
        sys.exit(1)

    print("\n📋 解析到以下持仓：")
    for i, h in enumerate(holdings, 1):
        print(f"  {i}. {h['fund_name']}({h['fund_code']}) "
              f"金额:{h['cost']} 收益率:{h['profit_ratio']}%")

    # 合并保存
    existing = load_portfolio()
    existing_map = {f["fund_code"]: f for f in existing if f.get("fund_code")}
    for h in holdings:
        if h.get("fund_code"):
            existing_map[h["fund_code"]] = h
    merged = list(existing_map.values())
    save_portfolio(merged)
    logger.info("💾 已保存 %d 只基金持仓", len(merged))

    # 自动触发一次简报
    print("\n🚀 自动生成首次建议...")
    result = app.invoke({"trigger": "daily_briefing"})
    briefing = result.get("briefing")
    if briefing:
        print("\n" + "=" * 50)
        print(format_all(briefing))
        print("=" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(description="基金投资助手")
    subparsers = parser.add_subparsers(dest="command")

    # 默认: 每日简报
    # add: 录入持仓
    add_parser = subparsers.add_parser("add", help="录入持仓")
    add_group = add_parser.add_mutually_exclusive_group(required=True)
    add_group.add_argument("--screenshot", "-s", help="截图文件路径")
    add_group.add_argument("--text", "-t", help="自然语言描述")

    args = parser.parse_args()

    if args.command == "add":
        if args.screenshot:
            run_add_from_screenshot(args.screenshot)
        else:
            run_add_from_text(args.text)
    else:
        run_daily_briefing()


if __name__ == "__main__":
    main()
