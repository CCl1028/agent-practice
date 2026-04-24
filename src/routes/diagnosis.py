"""基金诊断路由 — /api/fund-diagnosis, /api/fund-explanation"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends

from src.core.rate_limit import strict_rate_limit_dependency
from src.core.exceptions import BriefingTimeoutError, FundPalError, ValidationError
from src.graph import app as langgraph_app
from src.models.schemas import FundAnalysisRequest, FundDiagnosisResponse, FundExplanationResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/fund-diagnosis", response_model=FundDiagnosisResponse, dependencies=[Depends(strict_rate_limit_dependency)])
async def fund_diagnosis(request: FundAnalysisRequest):
    """基金诊断 — 分析基金是否值得买"""
    try:
        if not request.fund_code and not request.fund_name:
            raise ValidationError("fund_code 或 fund_name 必填")

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    langgraph_app.invoke,
                    {
                        "trigger": "fund_diagnosis",
                        "query_fund_code": request.fund_code,
                        "query_fund_name": request.fund_name,
                    },
                ),
                timeout=60.0,
            )
        except TimeoutError:
            logger.error("[基金诊断] 超时（60秒）")
            raise BriefingTimeoutError("诊断超时，请稍后重试") from None

        diagnosis = result.get("diagnosis")
        error = result.get("error")

        if error or not diagnosis:
            logger.error("[基金诊断] 分析失败: %s", error or "未知错误")
            raise FundPalError(error or "诊断失败")

        return FundDiagnosisResponse(
            rating=diagnosis.get("rating", ""),
            pros=diagnosis.get("pros", []),
            risks=diagnosis.get("risks", []),
            buy_recommendation=diagnosis.get("buy_recommendation", ""),
            buy_reason=diagnosis.get("buy_reason", ""),
            summary=diagnosis.get("summary", ""),
            profile=diagnosis.get("profile", {}),
        )

    except FundPalError:
        raise
    except Exception as e:
        logger.error("[基金诊断] 处理失败: %s", e, exc_info=True)
        raise FundPalError(f"诊断处理失败: {e}") from e


@router.post("/api/fund-explanation", response_model=FundExplanationResponse, dependencies=[Depends(strict_rate_limit_dependency)])
async def fund_explanation(request: FundAnalysisRequest):
    """基金分析 — 分析基金涨跌原因"""
    try:
        if not request.fund_code and not request.fund_name:
            raise ValidationError("fund_code 或 fund_name 必填")

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    langgraph_app.invoke,
                    {
                        "trigger": "fall_analysis",
                        "query_fund_code": request.fund_code,
                        "query_fund_name": request.fund_name,
                    },
                ),
                timeout=60.0,
            )
        except TimeoutError:
            logger.error("[基金分析] 超时（60秒）")
            raise BriefingTimeoutError("分析超时，请稍后重试") from None

        fall_analysis = result.get("fall_analysis")
        error = result.get("error")

        if error or not fall_analysis:
            logger.error("[基金分析] 分析失败: %s", error or "未知错误")
            raise FundPalError(error or "分析失败")

        return FundExplanationResponse(
            direction=fall_analysis.get("direction", ""),
            change_ratio=fall_analysis.get("change_ratio", 0),
            reasons=fall_analysis.get("reasons", []),
            outlook=fall_analysis.get("outlook", ""),
            summary=fall_analysis.get("summary", ""),
            perf_data=fall_analysis.get("perf_data", {}),
        )

    except FundPalError:
        raise
    except Exception as e:
        logger.error("[基金分析] 处理失败: %s", e, exc_info=True)
        raise FundPalError(f"分析处理失败: {e}") from e
