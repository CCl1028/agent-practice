"""持仓路由 — /api/portfolio/*"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from functools import partial
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from src.core.auth import verify_token
from src.core.rate_limit import rate_limit_dependency, strict_rate_limit_dependency
from src.core.exceptions import BriefingTimeoutError, FundPalError
from src.models.schemas import AddResult, HoldingsInput, ParseResult, PortfolioResponse, TextInput
from src.tools.nlp_input import parse_natural_language
from src.tools.portfolio_tools import load_portfolio, save_portfolio
from src.utils.holdings_utils import merge_holdings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """获取当前持仓"""
    holdings = load_portfolio()
    return PortfolioResponse(holdings=holdings, count=len(holdings))


@router.post("/api/portfolio/add-text", response_model=AddResult, dependencies=[Depends(verify_token), Depends(rate_limit_dependency)])
async def add_from_text(input: TextInput):
    """自然语言录入持仓"""
    try:
        new_holdings = parse_natural_language(input.text)
        if not new_holdings:
            return AddResult(added=[], total=0)
        existing = load_portfolio()
        merged = merge_holdings(existing, new_holdings)
        save_portfolio(merged)
        return AddResult(added=new_holdings, total=len(merged))
    except Exception as e:
        logger.error("add-text 失败: %s", e)
        raise FundPalError(f"录入失败: {e}") from e


@router.post("/api/portfolio/parse-text", response_model=ParseResult, dependencies=[Depends(verify_token), Depends(strict_rate_limit_dependency)])
async def parse_text(input: TextInput):
    """解析自然语言持仓描述（只解析不保存）"""
    try:
        func = partial(parse_natural_language, input.text, input.config)
        new_holdings = await asyncio.wait_for(asyncio.to_thread(func), timeout=45.0)
        return ParseResult(parsed=new_holdings or [])
    except TimeoutError:
        logger.error("parse-text 超时（45秒）")
        raise BriefingTimeoutError("解析超时，请稍后重试") from None
    except Exception as e:
        logger.error("parse-text 失败: %s", e)
        raise FundPalError(f"解析失败: {e}") from e


@router.post("/api/portfolio/add-screenshot", response_model=AddResult, dependencies=[Depends(verify_token), Depends(rate_limit_dependency)])
async def add_from_screenshot(file: UploadFile = File(...)):
    """截图识别录入持仓"""
    try:
        from src.tools.ocr_tools import process_screenshot

        suffix = Path(file.filename or "img.jpg").suffix
        contents = await file.read()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        new_holdings = process_screenshot(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)

        if not new_holdings:
            return AddResult(added=[], total=0)
        existing = load_portfolio()
        merged = merge_holdings(existing, new_holdings)
        save_portfolio(merged)
        return AddResult(added=new_holdings, total=len(merged))
    except Exception as e:
        logger.error("add-screenshot 失败: %s", e, exc_info=True)
        raise FundPalError(f"截图识别失败: {e}") from e


@router.post("/api/portfolio/parse-screenshot", response_model=ParseResult, dependencies=[Depends(verify_token), Depends(strict_rate_limit_dependency)])
async def parse_screenshot(
    file: UploadFile = File(...),
    config: Optional[str] = None,
):
    """截图识别持仓（只解析不保存）"""
    try:
        from src.tools.ocr_tools import process_screenshot
        import json as json_mod

        cfg = {}
        if config:
            try:
                cfg = json_mod.loads(config)
            except Exception:
                pass

        suffix = Path(file.filename or "img.jpg").suffix
        contents = await file.read()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        new_holdings = process_screenshot(tmp_path, config=cfg)
        Path(tmp_path).unlink(missing_ok=True)
        return ParseResult(parsed=new_holdings or [])
    except Exception as e:
        logger.error("parse-screenshot 失败: %s", e, exc_info=True)
        raise FundPalError(f"截图解析失败: {e}") from e


@router.delete("/api/portfolio/{fund_code}", dependencies=[Depends(verify_token)])
async def delete_holding(fund_code: str):
    """删除一只持仓"""
    existing = load_portfolio()
    filtered = [f for f in existing if f.get("fund_code") != fund_code]
    save_portfolio(filtered)
    return {"deleted": fund_code, "remaining": len(filtered)}


@router.post("/api/portfolio/refresh")
async def refresh_portfolio(input: Optional[HoldingsInput] = None):
    """根据最新净值更新市值和收益率（不修改服务器存储）"""
    from src.tools.market_tools import get_fund_nav

    holdings = input.holdings if input and input.holdings else []
    updated = []
    for h in holdings:
        fund_code = h.get("fund_code", "")
        if not fund_code:
            updated.append(h)
            continue

        item = {**h}
        try:
            nav_data = get_fund_nav(fund_code)
            current_nav = nav_data.get("current_nav", 0)
            item["current_nav"] = current_nav
            item["trend_5d"] = nav_data.get("trend_5d", [])

            cost_nav = h.get("cost_nav", 0)
            cost = h.get("cost", 0)

            if cost_nav and cost_nav > 0 and current_nav > 0:
                item["profit_ratio"] = round((current_nav - cost_nav) / cost_nav * 100, 2)
                shares = h.get("shares", 0)
                if not shares and cost > 0:
                    shares = cost / cost_nav
                if shares > 0:
                    item["shares"] = round(shares, 2)
                    item["market_value"] = round(shares * current_nav, 2)
                    item["profit_amount"] = round(shares * current_nav - shares * cost_nav, 2)
                else:
                    item["market_value"] = 0
            elif cost > 0 and current_nav > 0:
                old_ratio = h.get("profit_ratio", 0) or 0
                item["market_value"] = round(cost * (1 + old_ratio / 100), 2)
            else:
                item["market_value"] = h.get("cost", 0)
        except Exception as e:
            logger.warning("[持仓刷新] %s 获取净值失败: %s", fund_code, e)
            item["market_value"] = h.get("cost", 0)

        updated.append(item)

    return {"holdings": updated}
