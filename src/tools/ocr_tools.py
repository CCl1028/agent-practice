"""截图识别工具 — PaddleOCR 识别 + LLM 结构化解析"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, TEXT_MODEL

logger = logging.getLogger(__name__)

PARSE_PROMPT = """\
你是一个基金持仓数据解析专家。用户从基金App截图中提取了OCR文字，你需要从中识别出持仓信息。

请从文字中提取所有能找到的基金持仓，每只基金提取以下字段：
- fund_code: 基金代码（6位数字）
- fund_name: 基金名称
- cost: 持有金额（元），找不到就填 0
- cost_nav: 成本净值，找不到就填 0
- current_nav: 最新净值，找不到就填 0
- profit_ratio: 持有收益率（%），找不到就填 0
- hold_days: 持有天数，找不到就填 0

注意：
- 有些截图可能只有部分信息，尽量提取能找到的
- 收益率可能显示为 "+5.23%" 或 "-3.12%"，转为数字
- 如果找到买入时间，可以估算持有天数
- 如果实在无法识别，返回空数组

严格按以下 JSON 格式输出，不要输出其他内容：
[{"fund_code": "005827", "fund_name": "易方达蓝筹精选", "cost": 20000, "cost_nav": 2.15, "current_nav": 2.03, "profit_ratio": -5.6, "hold_days": 280}]
"""


def ocr_image(image_path: str) -> str:
    """用 PaddleOCR 识别图片中的文字。"""
    import os
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(lang="ch")
    results = ocr.predict(image_path)

    texts = []
    for result in results:
        rec_texts = result.get("rec_texts", None) if hasattr(result, "get") else result["rec_texts"]
        if rec_texts:
            texts.extend(rec_texts)

    full_text = "\n".join(texts)
    logger.info("[OCR] 识别到 %d 行文字", len(texts))
    return full_text


def parse_ocr_text(ocr_text: str) -> list[dict]:
    """用 LLM 从 OCR 文字中提取结构化持仓数据。"""
    if not ocr_text.strip():
        logger.warning("[OCR Parser] OCR 文字为空")
        return []

    llm = ChatOpenAI(
        model=TEXT_MODEL,
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        temperature=0,
    )

    response = llm.invoke([
        SystemMessage(content=PARSE_PROMPT),
        HumanMessage(content=f"以下是从基金App截图中OCR识别的文字：\n\n{ocr_text}"),
    ])

    text = response.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        holdings = json.loads(text)
        if isinstance(holdings, list):
            from src.tools.market_tools import get_fund_name_by_code

            # 补全缺失字段
            for h in holdings:
                h.setdefault("fund_code", "")
                h.setdefault("fund_name", "未知基金")
                h.setdefault("cost", 0)
                h.setdefault("cost_nav", 0)
                h.setdefault("current_nav", 0)
                h.setdefault("profit_ratio", 0)
                h.setdefault("hold_days", 0)
                h.setdefault("trend_5d", [])

                # 用真实 API 校正基金名称
                if h["fund_code"]:
                    real_name = get_fund_name_by_code(h["fund_code"])
                    if real_name:
                        if real_name != h["fund_name"]:
                            logger.info(
                                "[OCR Parser] 校正基金名称: %s → %s (代码 %s)",
                                h["fund_name"], real_name, h["fund_code"],
                            )
                        h["fund_name"] = real_name

            logger.info("[OCR Parser] 解析出 %d 只基金", len(holdings))
            return holdings
    except json.JSONDecodeError as e:
        logger.error("[OCR Parser] JSON 解析失败: %s", e)

    return []


def process_screenshot(image_path: str) -> list[dict]:
    """完整流程：截图 → OCR → LLM 解析 → 结构化持仓。"""
    path = Path(image_path)
    if not path.exists():
        logger.error("[Screenshot] 文件不存在: %s", image_path)
        return []

    logger.info("[Screenshot] 开始处理截图: %s", image_path)

    # Step 1: OCR 识别
    ocr_text = ocr_image(image_path)
    if not ocr_text:
        logger.warning("[Screenshot] OCR 未识别到文字")
        return []

    logger.info("[Screenshot] OCR 文字:\n%s", ocr_text)

    # Step 2: LLM 解析
    holdings = parse_ocr_text(ocr_text)
    return holdings
