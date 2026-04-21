"""JSON 解析辅助工具 — 从 briefing_agent / analysis_agent 提取的公共模块

T-010: 增强 LLM JSON 输出解析鲁棒性
T-016: 消除 _clean_json_text 在两个 agent 中的重复
"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)


def clean_json_text(text: str) -> str:
    """清理 LLM 输出的 JSON 文本中的常见问题。

    处理：
    - 去除 markdown 代码块标记（```json ... ```）
    - 去除尾逗号（如 {"a": 1,}）
    - 去除 JS 风格注释（// 和 /* */）
    - 去除 BOM 和特殊不可见字符
    """
    # 去除 markdown 代码块标记
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    # 去除 BOM
    text = text.lstrip("\ufeff")
    # 去除单行注释（// ...）— 但保留 URL 中的 //
    text = re.sub(r"(?<!:)//.*?(?=\n|$)", "", text)
    # 去除多行注释（/* ... */）
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # 去除对象/数组尾逗号（如 {"a": 1,} 或 [1, 2,]）
    text = re.sub(r",\s*([\]}])", r"\1", text)
    return text.strip()


def safe_parse_json(
    text: str,
    fallback: dict | list | None = None,
) -> dict | list | None:
    """安全解析 JSON，失败返回 fallback。

    流程：
    1. 清理 LLM 常见的不规范输出（尾逗号、注释、markdown 包裹等）
    2. 尝试 json.loads
    3. 失败时记录日志并返回 fallback

    Args:
        text: LLM 输出的原始文本
        fallback: 解析失败时的默认返回值

    Returns:
        解析后的 dict/list，或 fallback
    """
    if not text or not text.strip():
        return fallback

    cleaned = clean_json_text(text)
    try:
        result: dict | list = json.loads(cleaned)
        return result
    except json.JSONDecodeError as e:
        logger.warning("[JSON] 解析失败: %s\n原始文本（前500字）: %s", e, cleaned[:500])
        return fallback
