"""Pydantic 请求/响应模型 — 全部 API 共用"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


# ---- 通用输入 ----

class TextInput(BaseModel):
    text: str
    config: dict = {}


class HoldingsInput(BaseModel):
    holdings: list[dict] = []
    config: dict = {}


class PushTestInput(BaseModel):
    config: dict = {}


class ConfigUpdate(BaseModel):
    key: str
    value: str


class FundAnalysisRequest(BaseModel):
    fund_code: str = ""
    fund_name: str = ""


# ---- 通用输出 ----

class BriefingResponse(BaseModel):
    notification: str
    card: str
    report: str
    raw: dict


class PortfolioResponse(BaseModel):
    holdings: list[dict]
    count: int


class AddResult(BaseModel):
    added: list[dict]
    total: int


class ParseResult(BaseModel):
    parsed: list[dict]


class FundDiagnosisResponse(BaseModel):
    rating: str
    pros: list
    risks: list
    buy_recommendation: str
    buy_reason: str
    summary: str
    profile: Optional[dict] = None


class FundExplanationResponse(BaseModel):
    direction: str
    change_ratio: float
    reasons: list
    outlook: str
    summary: str
    perf_data: Optional[dict] = None
