from __future__ import annotations

import os
from pathlib import Path

os.environ["APPDATA"] = str(Path(__file__).resolve().parents[1] / ".pytest_appdata")

import whatsapp_helper


class FakeDriver:
    def __init__(self, page_source: str = ""):
        self.page_source = page_source
        self.scripts: list[str] = []
        self.script_results: list[object] = []
        self.keys_sent: list[object] = []

    def execute_script(self, script: str):
        self.scripts.append(script)
        if self.script_results:
            return self.script_results.pop(0)
        return None


class FakeElement:
    def __init__(self, driver: FakeDriver):
        self.driver = driver

    def send_keys(self, key):
        self.driver.keys_sent.append(key)


def test_logged_in_detection_accepts_whatsapp_business_home_shell(monkeypatch):
    monkeypatch.setattr(whatsapp_helper, "_find_visible_element", lambda *args, **kwargs: None)

    driver = FakeDriver(
        "<main>WhatsApp Business on Web</main>"
        "<aside>Search or start a new chat</aside>"
    )

    assert whatsapp_helper._logged_in_now(driver) is True


def test_logged_in_detection_rejects_qr_only_page(monkeypatch):
    monkeypatch.setattr(whatsapp_helper, "_find_visible_element", lambda *args, **kwargs: None)

    driver = FakeDriver("<main>Scan QR code to log in to WhatsApp Web</main>")

    assert whatsapp_helper._logged_in_now(driver) is False


def test_compose_ready_uses_current_message_box_selectors(monkeypatch):
    seen_selectors = []

    def fake_find(_driver, selectors, timeout=0):
        seen_selectors.extend(selectors)
        return object() if "div[aria-label='Type a message'][contenteditable='true']" in selectors else None

    monkeypatch.setattr(whatsapp_helper, "_find_visible_element", fake_find)

    assert whatsapp_helper._compose_ready(FakeDriver(), timeout=1) is True
    assert "div[contenteditable='true'][data-lexical-editor='true']" in seen_selectors


def test_send_button_uses_current_send_icon_selectors(monkeypatch):
    seen_selectors = []

    def fake_find(_driver, selectors, timeout=0):
        seen_selectors.extend(selectors)
        return object()

    monkeypatch.setattr(whatsapp_helper, "_find_visible_element", fake_find)

    assert whatsapp_helper._send_button(FakeDriver(), timeout=1) is not None
    assert "span[data-icon*='send']" in seen_selectors


def test_send_button_falls_back_to_dom_script(monkeypatch):
    driver = FakeDriver()
    sentinel = object()
    driver.script_results.append(sentinel)
    monkeypatch.setattr(whatsapp_helper, "_find_visible_element", lambda *args, **kwargs: None)

    assert whatsapp_helper._send_button(driver, timeout=0) is sentinel
    assert "data-icon" in driver.scripts[-1]


def test_wait_send_accepts_cleared_draft_as_sent(monkeypatch):
    monkeypatch.setattr(whatsapp_helper, "_send_button", lambda *args, **kwargs: None)
    monkeypatch.setattr(whatsapp_helper, "_message_draft_present", lambda _driver: False)

    assert whatsapp_helper._wait_manual_or_auto_send(
        FakeDriver(),
        manual_send_timeout=0,
        auto_send_fallback=True,
    ) is True


def test_click_send_control_uses_script_fallback(monkeypatch):
    driver = FakeDriver()
    driver.script_results.append(True)
    monkeypatch.setattr(whatsapp_helper, "_send_button", lambda *args, **kwargs: None)

    assert whatsapp_helper._click_send_control(driver) is True


def test_press_enter_to_send_uses_compose_box(monkeypatch):
    driver = FakeDriver()
    element = FakeElement(driver)
    monkeypatch.setattr(whatsapp_helper, "_compose_box", lambda _driver, timeout=0: element)

    assert whatsapp_helper._press_enter_to_send(driver) is True
    assert driver.keys_sent


def test_auto_send_uses_enter_fallback_when_click_does_not_clear_draft(monkeypatch):
    calls = {"draft": 0, "enter": 0}

    def draft_present(_driver):
        calls["draft"] += 1
        return calls["enter"] == 0

    monkeypatch.setattr(whatsapp_helper, "_send_button", lambda *args, **kwargs: object())
    monkeypatch.setattr(whatsapp_helper, "_click_send_control", lambda _driver: True)
    monkeypatch.setattr(whatsapp_helper, "_message_draft_present", draft_present)
    monkeypatch.setattr(whatsapp_helper, "_press_enter_to_send", lambda _driver: calls.__setitem__("enter", calls["enter"] + 1) or True)

    assert whatsapp_helper._wait_manual_or_auto_send(
        FakeDriver(),
        manual_send_timeout=0,
        auto_send_fallback=True,
    ) is True
    assert calls["enter"] == 1


def test_send_text_opens_default_browser_but_does_not_claim_sent_when_driver_session_is_not_ready(monkeypatch):
    opened = []

    monkeypatch.setattr(
        whatsapp_helper,
        "ensure_session_ready",
        lambda wait_for_login=0: {"ready": False, "state": "FAILED"},
    )
    monkeypatch.setattr(whatsapp_helper, "_open_default_browser", lambda url: opened.append(url) or True)

    assert whatsapp_helper.send_text("9847523353", "hello") is False
    assert opened
    assert "web.whatsapp.com/send?phone=" in opened[0]


def test_send_text_does_not_open_default_browser_when_login_is_pending(monkeypatch):
    opened = []

    monkeypatch.setattr(
        whatsapp_helper,
        "ensure_session_ready",
        lambda wait_for_login=0: {"ready": False, "state": "WAITING_FOR_LOGIN"},
    )
    monkeypatch.setattr(whatsapp_helper, "_open_default_browser", lambda url: opened.append(url) or True)

    assert whatsapp_helper.send_text("9847523353", "hello") is False
    assert opened == []


def test_default_browser_open_does_not_force_new_tab(monkeypatch):
    calls = []

    monkeypatch.setattr(
        whatsapp_helper.webbrowser,
        "open",
        lambda url, new=0, autoraise=True: calls.append((url, new, autoraise)) or True,
    )

    assert whatsapp_helper._open_default_browser("https://web.whatsapp.com")
    assert calls == [("https://web.whatsapp.com", 0, True)]


def test_edge_default_driver_failure_does_not_fall_back_to_chrome(monkeypatch):
    attempted = []

    class FakeWebDriver:
        class Edge:
            def __init__(self, *args, **kwargs):
                attempted.append("edge")
                raise RuntimeError("edge failed")

        class Chrome:
            def __init__(self, *args, **kwargs):
                attempted.append("chrome")
                raise RuntimeError("chrome should not be attempted")

    class FakeOptions:
        def add_argument(self, *_args, **_kwargs):
            pass

        def add_experimental_option(self, *_args, **_kwargs):
            pass

    class FakeService:
        def __init__(self, *_args, **_kwargs):
            pass

    monkeypatch.setattr(whatsapp_helper, "_detect_browser", lambda: "edge")
    monkeypatch.setattr(whatsapp_helper, "_driver", None)

    import sys
    import types

    selenium_mod = types.ModuleType("selenium")
    webdriver_mod = types.ModuleType("selenium.webdriver")
    webdriver_mod.Edge = FakeWebDriver.Edge
    webdriver_mod.Chrome = FakeWebDriver.Chrome
    edge_options_mod = types.ModuleType("selenium.webdriver.edge.options")
    edge_options_mod.Options = FakeOptions
    edge_service_mod = types.ModuleType("selenium.webdriver.edge.service")
    edge_service_mod.Service = FakeService

    monkeypatch.setitem(sys.modules, "selenium", selenium_mod)
    monkeypatch.setitem(sys.modules, "selenium.webdriver", webdriver_mod)
    monkeypatch.setitem(sys.modules, "selenium.webdriver.edge.options", edge_options_mod)
    monkeypatch.setitem(sys.modules, "selenium.webdriver.edge.service", edge_service_mod)

    try:
        whatsapp_helper._get_driver()
    except RuntimeError:
        pass

    assert attempted
    assert set(attempted) == {"edge"}
