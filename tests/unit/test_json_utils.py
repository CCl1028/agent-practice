"""JSON 工具单元测试 — clean_json_text + safe_parse_json"""

import pytest
from src.utils.json_utils import clean_json_text, safe_parse_json


class TestCleanJsonText:
    """clean_json_text 测试"""

    def test_plain_json(self):
        """正常 JSON 不变"""
        text = '{"a": 1}'
        assert clean_json_text(text) == '{"a": 1}'

    def test_markdown_wrapped(self):
        """去除 markdown ```json``` 包裹"""
        text = '```json\n{"a": 1}\n```'
        assert clean_json_text(text) == '{"a": 1}'

    def test_markdown_no_lang(self):
        """去除 ``` 包裹（无语言标记）"""
        text = '```\n{"a": 1}\n```'
        assert clean_json_text(text) == '{"a": 1}'

    def test_trailing_comma_object(self):
        """去除对象尾逗号"""
        text = '{"a": 1, "b": 2,}'
        result = clean_json_text(text)
        assert result == '{"a": 1, "b": 2}'

    def test_trailing_comma_array(self):
        """去除数组尾逗号"""
        text = '[1, 2, 3,]'
        result = clean_json_text(text)
        assert result == '[1, 2, 3]'

    def test_single_line_comment(self):
        """去除单行注释"""
        text = '{"a": 1} // this is comment'
        result = clean_json_text(text)
        assert "//" not in result

    def test_url_preserved(self):
        """URL 中的 // 不被误删"""
        text = '{"url": "https://example.com"}'
        result = clean_json_text(text)
        assert "https://example.com" in result

    def test_bom(self):
        """去除 BOM"""
        text = '\ufeff{"a": 1}'
        result = clean_json_text(text)
        assert result == '{"a": 1}'

    def test_multiline_comment(self):
        """去除多行注释"""
        text = '{"a": 1 /* comment */}'
        result = clean_json_text(text)
        assert "/*" not in result

    def test_empty_string(self):
        """空字符串"""
        assert clean_json_text("") == ""


class TestSafeParseJson:
    """safe_parse_json 测试"""

    def test_valid_dict(self):
        """正常 dict"""
        result = safe_parse_json('{"a": 1}')
        assert result == {"a": 1}

    def test_valid_list(self):
        """正常 list"""
        result = safe_parse_json('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_with_trailing_comma(self):
        """带尾逗号的 JSON"""
        result = safe_parse_json('{"a": 1,}')
        assert result == {"a": 1}

    def test_with_markdown(self):
        """markdown 包裹"""
        result = safe_parse_json('```json\n{"a": 1}\n```')
        assert result == {"a": 1}

    def test_invalid_json_returns_fallback(self):
        """无效 JSON 返回 fallback"""
        result = safe_parse_json("not json", fallback={"error": True})
        assert result == {"error": True}

    def test_empty_returns_fallback(self):
        """空字符串返回 fallback"""
        result = safe_parse_json("", fallback=[])
        assert result == []

    def test_none_fallback(self):
        """默认 fallback 是 None"""
        result = safe_parse_json("bad")
        assert result is None

    def test_whitespace_only(self):
        """纯空白返回 fallback"""
        result = safe_parse_json("   \n  ", fallback={})
        assert result == {}
