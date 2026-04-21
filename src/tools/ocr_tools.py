"""截图识别工具 — 多模态 LLM 识别 + 结构化解析（无需 PaddleOCR）"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    TEXT_MODEL,
    VISION_API_KEY,
    VISION_BASE_URL,
    VISION_MODEL,
)

logger = logging.getLogger(__name__)

PARSE_PROMPT = """\
你是一个基金持仓数据解析专家。用户会发送一张基金App的截图，你需要从中识别出持仓信息。

首先判断截图类型：
- "detail": 单只基金的持仓详情页（通常有净值走势图、详细数据）
- "list": 持仓列表页（多只基金一览，每只显示简要信息）

然后从截图中提取所有能找到的基金持仓，每只基金提取以下字段：
- fund_code: 基金代码（6位数字）
- fund_name: 基金名称
- cost: 持有金额/市值（元），找不到就填 0
- cost_nav: 成本净值/持仓成本价，找不到就填 0
- current_nav: 最新净值，找不到就填 0
- profit_ratio: 持有收益率（%），找不到就填 0
- profit_amount: 持有收益金额（元），找不到就填 0
- shares: 持有份额，找不到就填 0

注意：
- 有些截图可能只有部分信息，尽量提取能找到的
- 收益率可能显示为 "+5.23%" 或 "-3.12%"，转为数字（不带%号）
- 持有份额可能显示为 "1234.56份"，提取数字部分
- 如果实在无法识别，返回空数组

严格按以下 JSON 格式输出，不要输出其他内容：
{"screenshot_type": "detail", "holdings": [{"fund_code": "005827", "fund_name": "易方达蓝筹精选", "cost": 20000, "cost_nav": 2.15, "current_nav": 2.03, "profit_ratio": -5.6, "profit_amount": -1120, "shares": 9302.33}]}
"""

PARSE_TEXT_PROMPT = """\
你是一个基金持仓数据解析专家。用户从基金App截图中提取了OCR文字，你需要从中识别出持仓信息。

请从文字中提取所有能找到的基金持仓，每只基金提取以下字段：
- fund_code: 基金代码（6位数字）
- fund_name: 基金名称
- cost: 持有金额/市值（元），找不到就填 0
- cost_nav: 成本净值/持仓成本价，找不到就填 0
- current_nav: 最新净值，找不到就填 0
- profit_ratio: 持有收益率（%），找不到就填 0
- profit_amount: 持有收益金额（元），找不到就填 0
- shares: 持有份额，找不到就填 0

注意：
- 有些截图可能只有部分信息，尽量提取能找到的
- 收益率可能显示为 "+5.23%" 或 "-3.12%"，转为数字（不带%号）
- 持有份额可能显示为 "1234.56份"，提取数字部分
- 如果实在无法识别，返回空数组

严格按以下 JSON 格式输出，不要输出其他内容：
[{"fund_code": "005827", "fund_name": "易方达蓝筹精选", "cost": 20000, "cost_nav": 2.15, "current_nav": 2.03, "profit_ratio": -5.6, "profit_amount": -1120, "shares": 9302.33}]
"""


def _image_to_base64_url(image_path: str) -> str:
    """将图片文件转为 base64 data URL。"""
    path = Path(image_path)
    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type:
        mime_type = "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def ocr_image_with_vision(image_path: str, config: dict | None = None) -> list[dict]:
    """用多模态 LLM 直接从图片中识别并提取持仓数据。

    Args:
        image_path: 图片文件路径
        config: 可选配置（当前不使用，视觉模型固定使用服务端配置）
    """
    # 视觉模型固定使用服务端环境变量配置（硅基流动），不使用前端传入的配置
    api_key = VISION_API_KEY
    base_url = VISION_BASE_URL
    model = VISION_MODEL

    # 检查 API Key 是否配置
    if not api_key:
        raise ValueError(
            "未配置视觉模型 API Key。请在设置中填写 API Key，或配置 VISION_API_KEY 环境变量。\n"
            "提示：需要支持图片输入的多模态模型（如 GPT-4o、GLM-4V、Qwen-VL）"
        )

    # 检查是否使用了不支持图片的模型
    non_vision_models = ["deepseek-chat", "deepseek-coder", "gpt-3.5-turbo", "gpt-4-turbo"]
    if model.lower() in [m.lower() for m in non_vision_models]:
        logger.warning(
            "[Vision OCR] 警告：%s 模型不支持图片输入！建议使用 gpt-4o、glm-4v 或 qwen-vl 等多模态模型", model
        )

    logger.info("[Vision OCR] 使用多模态模型: %s (base_url: %s)", model, base_url)

    image_url = _image_to_base64_url(image_path)

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
        max_tokens=2000,
        timeout=60,  # 增加超时时间，图片处理需要更长时间
    )

    try:
        response = llm.invoke(
            [
                SystemMessage(content=PARSE_PROMPT),
                HumanMessage(
                    content=[
                        {"type": "text", "text": "请识别这张基金App截图中的持仓信息："},
                        {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
                    ]
                ),
            ]
        )
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid api key" in error_msg or "authentication" in error_msg:
            raise ValueError(f"API Key 无效或已过期，请检查配置: {e}") from e
        elif "rate limit" in error_msg:
            raise ValueError(f"API 请求频率超限，请稍后重试: {e}") from e
        elif "model" in error_msg and ("not found" in error_msg or "does not exist" in error_msg):
            raise ValueError(
                f"模型 {model} 不存在或不支持。\n当前 base_url: {base_url}\n请检查模型配置是否正确: {e}"
            ) from e
        elif "image" in error_msg or "vision" in error_msg or "multimodal" in error_msg:
            raise ValueError(
                f"模型 {model} 可能不支持图片输入。\n请使用支持图片的多模态模型（如 gpt-4o、glm-4v、Qwen-VL）: {e}"
            ) from e
        else:
            raise ValueError(f"视觉模型调用失败: {e}") from e

    text = response.content.strip()
    logger.info("[Vision OCR] LLM 返回:\n%s", text)

    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        holdings = json.loads(text)
        # 兼容新格式 {"screenshot_type": "...", "holdings": [...]}
        if isinstance(holdings, dict):
            screenshot_type = holdings.get("screenshot_type", "unknown")
            logger.info("[Vision OCR] 截图类型: %s", screenshot_type)
            holdings = holdings.get("holdings", [])
        if isinstance(holdings, list):
            return holdings
    except json.JSONDecodeError as e:
        logger.error("[Vision OCR] JSON 解析失败: %s\n原始返回: %s", e, text[:500])

    return []


def ocr_image(image_path: str) -> str:
    """用 PaddleOCR 识别图片中的文字（备选方案）。"""
    try:
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
    except ImportError:
        logger.warning("[OCR] PaddleOCR 未安装，将使用多模态 LLM 方案")
        return ""
    except Exception as e:
        logger.error("[OCR] PaddleOCR 识别失败: %s", e)
        return ""


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

    response = llm.invoke(
        [
            SystemMessage(content=PARSE_TEXT_PROMPT),
            HumanMessage(content=f"以下是从基金App截图中OCR识别的文字：\n\n{ocr_text}"),
        ]
    )

    text = response.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        holdings = json.loads(text)
        if isinstance(holdings, list):
            return holdings
    except json.JSONDecodeError as e:
        logger.error("[OCR Parser] JSON 解析失败: %s", e)

    return []


def _enrich_holdings(holdings: list[dict]) -> list[dict]:
    """补全字段、反算成本净值、校正基金代码和名称。

    LLM 识别的基金代码可能不准确（尤其当截图中不显示代码时），
    通过 verify_and_fix_fund 进行双向校验和修正。

    成本净值反算策略（按优先级）：
    1. 如果 cost_nav 已有值 → 直接使用
    2. 如果有 shares 和 cost → cost_nav = (cost - profit_amount) / shares
    3. 如果有 current_nav 和 profit_ratio → cost_nav = current_nav / (1 + profit_ratio/100)
    4. 如果有 cost 和 profit_amount → cost_nav 通过投入本金反算
    """
    from src.tools.market_tools import verify_and_fix_fund

    for h in holdings:
        h.setdefault("fund_code", "")
        h.setdefault("fund_name", "未知基金")
        h.setdefault("cost", 0)
        h.setdefault("cost_nav", 0)
        h.setdefault("current_nav", 0)
        h.setdefault("profit_ratio", 0)
        h.setdefault("profit_amount", 0)
        h.setdefault("shares", 0)
        h.setdefault("hold_days", 0)
        h.setdefault("trend_5d", [])

        # ---- P0: 成本净值反算 ----
        cost_nav = h["cost_nav"]
        current_nav = h["current_nav"]
        profit_ratio = h["profit_ratio"]
        profit_amount = h["profit_amount"]
        shares = h["shares"]
        cost = h["cost"]

        if cost_nav <= 0:
            # 策略2: 有份额和持仓金额 → 反算成本净值
            if shares > 0 and cost > 0:
                invested = cost - profit_amount  # 投入本金
                cost_nav = round(invested / shares, 4)
                logger.info(
                    "[反算] %s: cost_nav = (%.2f - %.2f) / %.2f = %.4f",
                    h["fund_name"],
                    cost,
                    profit_amount,
                    shares,
                    cost_nav,
                )
                h["cost_nav"] = cost_nav

            # 策略3: 有当前净值和收益率 → 反算
            elif current_nav > 0 and profit_ratio != 0:
                cost_nav = round(current_nav / (1 + profit_ratio / 100), 4)
                logger.info(
                    "[反算] %s: cost_nav = %.4f / (1 + %.2f%%) = %.4f",
                    h["fund_name"],
                    current_nav,
                    profit_ratio,
                    cost_nav,
                )
                h["cost_nav"] = cost_nav

            # 策略4: 有持仓金额和收益金额 → 反算投入本金，再结合份额
            elif cost > 0 and profit_amount != 0 and shares > 0:
                invested = cost - profit_amount
                cost_nav = round(invested / shares, 4)
                h["cost_nav"] = cost_nav

        # ---- 补算 shares（如果缺失但有 cost 和 cost_nav）----
        if h["shares"] <= 0 and h["cost"] > 0 and h["cost_nav"] > 0:
            h["shares"] = round(h["cost"] / h["cost_nav"], 2)
            logger.info(
                "[补算] %s: shares = %.2f / %.4f = %.2f",
                h["fund_name"],
                h["cost"],
                h["cost_nav"],
                h["shares"],
            )

        # 双向校验：代码↔名称，修正 LLM 可能猜错的代码
        old_code, old_name = h["fund_code"], h["fund_name"]
        corrected_code, corrected_name = verify_and_fix_fund(old_code, old_name)

        if corrected_code != old_code or corrected_name != old_name:
            logger.info(
                "[OCR Parser] 校正基金: %s(%s) → %s(%s)",
                old_name,
                old_code,
                corrected_name,
                corrected_code,
            )
        h["fund_code"] = corrected_code
        h["fund_name"] = corrected_name

    return holdings


def process_screenshot(image_path: str, config: dict | None = None) -> list[dict]:
    """完整流程：截图 → 识别 → 结构化持仓。

    优先使用多模态 LLM 直接识别图片；
    如果 VISION_MODEL 不可用，则回退到 PaddleOCR + LLM 解析。

    Args:
        image_path: 图片文件路径
        config: 可选配置，支持传入 OPENAI_API_KEY 和 OPENAI_BASE_URL
    """
    path = Path(image_path)
    if not path.exists():
        logger.error("[Screenshot] 文件不存在: %s", image_path)
        return []

    logger.info("[Screenshot] 开始处理截图: %s", image_path)

    # 方案 1: 多模态 LLM 直接识别（推荐）
    vision_error = None
    try:
        holdings = ocr_image_with_vision(image_path, config=config)
        if holdings:
            logger.info("[Screenshot] 多模态识别成功，识别到 %d 只基金", len(holdings))
            return _enrich_holdings(holdings)
        else:
            logger.warning("[Screenshot] 多模态模型返回空结果，可能无法识别截图内容")
    except ValueError as e:
        # 配置错误，直接抛出让用户知道
        vision_error = str(e)
        logger.error("[Screenshot] 视觉模型配置错误: %s", e)
    except Exception as e:
        vision_error = str(e)
        logger.warning("[Screenshot] 多模态识别失败，尝试回退到 OCR 方案: %s", e)

    # 方案 2: PaddleOCR + LLM 解析（回退）
    ocr_text = ocr_image(image_path)
    if ocr_text:
        logger.info("[Screenshot] OCR 文字:\n%s", ocr_text)
        holdings = parse_ocr_text(ocr_text)
        if holdings:
            return _enrich_holdings(holdings)

    # 所有方案都失败，给出详细提示
    error_msg = "[Screenshot] 未能从截图中识别到基金持仓信息"
    if vision_error:
        error_msg += f"\n视觉模型错误: {vision_error}"
        error_msg += "\n建议检查: 1) API Key 是否正确配置 2) 使用支持图片的多模态模型"
    logger.warning(error_msg)
    return []
