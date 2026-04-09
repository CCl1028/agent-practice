"""P4: 识别后确认环节的测试

验证:
1. 前端 HTML 包含确认弹窗的 DOM 元素
2. 前端 JS 包含确认流程的核心函数
3. 截图识别流程不再直接保存（调 parse-screenshot 而非 add-screenshot）
4. 文本识别流程中新增持仓走确认弹窗
5. 后端 parse API 只解析不保存
"""

import os
import re
import pytest

HTML_PATH = os.path.join(
    os.path.dirname(__file__), "..", "web", "index.html"
)


@pytest.fixture(scope="module")
def html_content():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        return f.read()


class TestConfirmDrawerDOM:
    """验证确认弹窗的 DOM 结构是否存在"""

    def test_confirm_overlay_exists(self, html_content):
        assert 'id="confirm-overlay"' in html_content

    def test_confirm_drawer_exists(self, html_content):
        assert 'id="confirm-drawer"' in html_content

    def test_confirm_list_exists(self, html_content):
        assert 'id="confirm-list"' in html_content

    def test_confirm_save_button_exists(self, html_content):
        assert 'id="confirm-save-btn"' in html_content

    def test_confirm_cancel_button(self, html_content):
        assert "confirm-cancel-btn" in html_content

    def test_confirm_screenshot_type_container(self, html_content):
        assert 'id="confirm-screenshot-type"' in html_content

    def test_confirm_drawer_title(self, html_content):
        assert 'id="confirm-drawer-title"' in html_content


class TestConfirmDrawerCSS:
    """验证确认弹窗的样式是否定义"""

    def test_confirm_drawer_style(self, html_content):
        assert ".confirm-drawer" in html_content

    def test_confirm_item_style(self, html_content):
        assert ".confirm-item" in html_content

    def test_confirm_fields_grid(self, html_content):
        assert ".confirm-fields" in html_content

    def test_confirm_field_input_edited(self, html_content):
        assert ".confirm-field input.edited" in html_content

    def test_confirm_actions_style(self, html_content):
        assert ".confirm-actions" in html_content

    def test_confirm_save_btn_style(self, html_content):
        assert ".confirm-save-btn" in html_content

    def test_confirm_screenshot_type_style(self, html_content):
        assert ".confirm-screenshot-type" in html_content


class TestConfirmJSFunctions:
    """验证确认弹窗的 JS 函数是否存在"""

    def test_openConfirmDrawer_defined(self, html_content):
        assert "function openConfirmDrawer(" in html_content

    def test_closeConfirmDrawer_defined(self, html_content):
        assert "function closeConfirmDrawer(" in html_content

    def test_renderConfirmList_defined(self, html_content):
        assert "function renderConfirmList(" in html_content

    def test_updateConfirmField_defined(self, html_content):
        assert "function updateConfirmField(" in html_content

    def test_removeConfirmItem_defined(self, html_content):
        assert "function removeConfirmItem(" in html_content

    def test_confirmSaveHoldings_defined(self, html_content):
        assert "function confirmSaveHoldings(" in html_content

    def test_escapeAttr_defined(self, html_content):
        assert "function escapeAttr(" in html_content

    def test_confirmPendingHoldings_variable(self, html_content):
        assert "confirmPendingHoldings" in html_content


class TestScreenshotFlowUsesConfirm:
    """验证截图识别流程改为使用确认弹窗"""

    def test_screenshot_calls_openConfirmDrawer(self, html_content):
        """addFromScreenshot 中应调用 openConfirmDrawer"""
        # 提取 addFromScreenshot 函数体
        match = re.search(
            r"async function addFromScreenshot\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match, "addFromScreenshot 函数不存在"
        fn_body = match.group(0)
        assert "openConfirmDrawer(" in fn_body, \
            "addFromScreenshot 应该调用 openConfirmDrawer"

    def test_screenshot_no_direct_save(self, html_content):
        """addFromScreenshot 中不应直接调用 saveLocalPortfolio"""
        match = re.search(
            r"async function addFromScreenshot\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        fn_body = match.group(0)
        assert "saveLocalPortfolio(" not in fn_body, \
            "addFromScreenshot 不应直接保存，应走确认流程"

    def test_screenshot_uses_parse_endpoint(self, html_content):
        """截图应使用 parse-screenshot 端点（只解析不保存）"""
        match = re.search(
            r"async function addFromScreenshot\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        fn_body = match.group(0)
        assert "/api/portfolio/parse-screenshot" in fn_body
        assert "/api/portfolio/add-screenshot" not in fn_body


class TestTextFlowUsesConfirm:
    """验证文本识别流程中新增持仓走确认弹窗"""

    def test_text_new_holdings_use_confirm(self, html_content):
        """addFromText 中新增持仓应走 openConfirmDrawer"""
        match = re.search(
            r"async function addFromText\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match, "addFromText 函数不存在"
        fn_body = match.group(0)
        assert "openConfirmDrawer(" in fn_body, \
            "addFromText 新增持仓应走确认弹窗"

    def test_text_trade_still_direct(self, html_content):
        """addFromText 中交易操作（buy/sell）仍然直接执行"""
        match = re.search(
            r"async function addFromText\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        fn_body = match.group(0)
        assert "addTransaction(tx)" in fn_body, \
            "交易操作仍然应该直接调用 addTransaction"

    def test_text_uses_parse_endpoint(self, html_content):
        """文本识别应使用 parse-text 端点"""
        match = re.search(
            r"async function addFromText\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        fn_body = match.group(0)
        assert "/api/portfolio/parse-text" in fn_body


class TestConfirmSaveFlow:
    """验证确认保存的逻辑"""

    def test_confirmSave_calls_saveLocalPortfolio(self, html_content):
        """confirmSaveHoldings 应调用 saveLocalPortfolio"""
        match = re.search(
            r"function confirmSaveHoldings\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match, "confirmSaveHoldings 函数不存在"
        fn_body = match.group(0)
        assert "saveLocalPortfolio(" in fn_body

    def test_confirmSave_merges_with_existing(self, html_content):
        """确认保存应合并到已有持仓（而非覆盖）"""
        match = re.search(
            r"function confirmSaveHoldings\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        fn_body = match.group(0)
        assert "getLocalPortfolio()" in fn_body
        assert "existingMap" in fn_body

    def test_confirmSave_loads_estimation(self, html_content):
        """确认保存后应拉取新基金估值"""
        match = re.search(
            r"function confirmSaveHoldings\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        fn_body = match.group(0)
        assert "loadEstimationForNew(" in fn_body

    def test_confirmSave_closes_drawer(self, html_content):
        """确认保存后应关闭弹窗"""
        match = re.search(
            r"function confirmSaveHoldings\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        fn_body = match.group(0)
        assert "closeConfirmDrawer()" in fn_body


class TestConfirmFieldEditing:
    """验证确认弹窗支持字段编辑"""

    def test_render_has_fund_name_input(self, html_content):
        """确认弹窗应显示基金名称输入框"""
        match = re.search(
            r"function renderConfirmList\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        fn_body = match.group(0)
        assert "'fund_name'" in fn_body

    def test_render_has_fund_code_input(self, html_content):
        match = re.search(
            r"function renderConfirmList\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        assert "'fund_code'" in match.group(0)

    def test_render_has_cost_input(self, html_content):
        match = re.search(
            r"function renderConfirmList\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        assert "'cost'" in match.group(0)

    def test_render_has_cost_nav_input(self, html_content):
        match = re.search(
            r"function renderConfirmList\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        assert "'cost_nav'" in match.group(0)

    def test_render_has_shares_input(self, html_content):
        match = re.search(
            r"function renderConfirmList\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        assert "'shares'" in match.group(0)

    def test_render_has_profit_fields(self, html_content):
        match = re.search(
            r"function renderConfirmList\(\).*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        fn_body = match.group(0)
        assert "'profit_ratio'" in fn_body
        assert "'profit_amount'" in fn_body

    def test_edit_highlight_class(self, html_content):
        """编辑后的输入框应有 edited class"""
        match = re.search(
            r"function updateConfirmField\(.*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        fn_body = match.group(0)
        assert "'edited'" in fn_body

    def test_remove_item_uses_splice(self, html_content):
        """删除确认项应使用 splice"""
        match = re.search(
            r"function removeConfirmItem\(.*?\n\}",
            html_content,
            re.DOTALL,
        )
        assert match
        assert "splice(" in match.group(0)


class TestBackendParseAPIsExist:
    """验证后端有 parse-only 的 API（不保存）"""

    def test_parse_screenshot_route_exists(self):
        """server.py 中应有 /api/portfolio/parse-screenshot"""
        import importlib
        import server as srv
        routes = [r.path for r in srv.app.routes]
        assert "/api/portfolio/parse-screenshot" in routes

    def test_parse_text_route_exists(self):
        """server.py 中应有 /api/portfolio/parse-text"""
        import importlib
        import server as srv
        routes = [r.path for r in srv.app.routes]
        assert "/api/portfolio/parse-text" in routes
