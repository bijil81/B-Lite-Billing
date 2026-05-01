# -*- coding: utf-8 -*-
"""
whatsapp_helper.py - BOBY'S Salon V5.1 WhatsApp session controller

Goals:
- persistent browser profile
- single reusable WhatsApp Web tab
- explicit login/session state
- no false "sent" success
- manual send window with auto-send fallback

Public API:
- ensure_session_ready()
- open_whatsapp_web()
- check_login_status()
- get_session_snapshot()
- send_text()
- send_image()
- bulk_send()
"""

import atexit
import os
import threading
import time
import urllib.parse
import webbrowser

from utils import DATA_DIR, app_log, validate_phone

PROFILE_DIR = os.path.join(DATA_DIR, "wa_browser_profile")
DRIVER_CACHE = os.path.join(DATA_DIR, "wa_driver_cache")

os.makedirs(PROFILE_DIR, exist_ok=True)
os.makedirs(DRIVER_CACHE, exist_ok=True)

os.environ["WDM_LOCAL"] = "1"
os.environ["WDM_CACHE_PATH"] = DRIVER_CACHE

WA_BASE = "https://web.whatsapp.com"

STATE_NOT_STARTED = "NOT_STARTED"
STATE_STARTING_BROWSER = "STARTING_BROWSER"
STATE_OPENING_WHATSAPP = "OPENING_WHATSAPP"
STATE_WAITING_FOR_LOGIN = "WAITING_FOR_LOGIN"
STATE_READY = "READY"
STATE_DEFAULT_BROWSER_OPEN = "DEFAULT_BROWSER_OPEN"
STATE_OPENING_CHAT = "OPENING_CHAT"
STATE_WAITING_MANUAL_SEND = "WAITING_MANUAL_SEND"
STATE_AUTO_SENDING = "AUTO_SENDING"
STATE_SENT = "SENT"
STATE_FAILED = "FAILED"
STATE_BROWSER_CLOSED = "BROWSER_CLOSED"

_driver = None
_driver_lock = threading.Lock()
_session_lock = threading.Lock()
_session = {
    "state": STATE_NOT_STARTED,
    "message": "WhatsApp not started",
    "last_error": "",
    "updated_at": 0.0,
}


def _set_state(state: str, message: str, error: str = "") -> None:
    with _session_lock:
        _session["state"] = state
        _session["message"] = message
        _session["last_error"] = error
        _session["updated_at"] = time.time()
    if state == STATE_FAILED and error:
        app_log(f"[whatsapp_helper] {message}: {error}")


def get_session_snapshot() -> dict:
    with _session_lock:
        return dict(_session)


def _get_country_code() -> str:
    try:
        from salon_settings import get_settings
        return str(get_settings().get("country_code", "91")).strip() or "91"
    except Exception:
        return "91"


def build_billing_whatsapp_text(raw_text: str, footer_phone: str = "") -> str:
    from salon_settings import get_settings

    billing_mode = get_settings().get("billing_mode", "mixed")
    show_services = billing_mode in ("mixed", "service_only")
    show_products = billing_mode in ("mixed", "product_only")

    lines = (raw_text or "").splitlines()
    wa_lines: list[str] = []
    in_services = False
    in_products = False

    for ln in lines:
        stripped = ln.rstrip()
        upper = stripped.upper().strip()

        if upper == "SERVICES":
            in_services = True
            in_products = False
            if show_services:
                wa_lines.append(stripped)
            continue
        if upper == "PRODUCTS":
            in_services = False
            in_products = True
            if show_products:
                wa_lines.append(stripped)
            continue

        if in_services and not show_services:
            if upper.startswith("PRODUCTS"):
                in_services = False
                in_products = True
                if show_products:
                    wa_lines.append(stripped)
            elif upper.startswith("SERVICES SUBTOTAL") or not upper:
                in_services = False
            else:
                continue

        if in_products and not show_products:
            if upper.startswith("PRODUCTS SUBTOTAL") or not upper:
                in_products = False
            else:
                continue

        if "TOTAL" in upper or "INV:" in stripped:
            wa_lines.append("*" + stripped + "*")
        elif "====" in stripped:
            wa_lines.append("\u2550" * 30)
        else:
            wa_lines.append(stripped)

    while wa_lines and not wa_lines[-1].strip():
        wa_lines.pop()
    msg = "\n".join(wa_lines)
    if footer_phone:
        msg += f"\n\nFor appointments: {footer_phone}"
    return msg


def _detect_browser() -> str:
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice",
        )
        prog_id, _ = winreg.QueryValueEx(key, "ProgId")
        winreg.CloseKey(key)
        p = str(prog_id).lower()
        if "chrome" in p or "brave" in p:
            return "chrome"
        if "edge" in p:
            return "edge"
        if "firefox" in p:
            return "firefox"
    except Exception:
        pass

    browser_paths = {
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        "firefox": [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        ],
    }
    for name, paths in browser_paths.items():
        if any(os.path.exists(path) for path in paths):
            return name
    return "edge"


def _find_cached_driver(name: str):
    for root, _, files in os.walk(DRIVER_CACHE):
        for file_name in files:
            if name.lower() in file_name.lower() and file_name.lower().endswith(".exe"):
                return os.path.join(root, file_name)
    return None


def _driver_alive(drv) -> bool:
    try:
        _ = drv.current_url
        _ = drv.window_handles
        return True
    except Exception:
        return False


def _get_driver(headless: bool = False):
    global _driver
    with _driver_lock:
        if _driver is not None and _driver_alive(_driver):
            return _driver
        if _driver is not None:
            try:
                _driver.quit()
            except Exception:
                pass
            _driver = None

        _set_state(STATE_STARTING_BROWSER, "Starting WhatsApp browser...")

        try:
            from selenium import webdriver
        except ImportError as exc:
            raise ImportError(
                "selenium not installed. Run: pip install selenium webdriver-manager"
            ) from exc

        browser = _detect_browser()
        common_args = [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
        ]
        if headless:
            common_args.extend(["--headless=new", "--disable-gpu"])

        drv = None
        error_msg = ""

        if browser == "edge":
            try:
                from selenium.webdriver.edge.options import Options
                from selenium.webdriver.edge.service import Service

                opts = Options()
                opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
                opts.add_argument("--profile-directory=WA_Profile")
                opts.add_experimental_option("excludeSwitches", ["enable-automation"])
                for arg in common_args:
                    opts.add_argument(arg)
                cached = _find_cached_driver("msedgedriver")
                if cached:
                    drv = webdriver.Edge(service=Service(cached), options=opts)
                else:
                    try:
                        from webdriver_manager.microsoft import EdgeChromiumDriverManager

                        drv = webdriver.Edge(
                            service=Service(EdgeChromiumDriverManager().install()),
                            options=opts,
                        )
                    except Exception:
                        drv = webdriver.Edge(options=opts)
            except Exception as exc:
                error_msg = str(exc)
                browser = ""

        if browser == "chrome" and drv is None:
            try:
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.chrome.service import Service

                opts = Options()
                opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
                opts.add_argument("--profile-directory=WA_Profile")
                opts.add_experimental_option("excludeSwitches", ["enable-automation"])
                for arg in common_args:
                    opts.add_argument(arg)
                cached = _find_cached_driver("chromedriver")
                if cached:
                    drv = webdriver.Chrome(service=Service(cached), options=opts)
                else:
                    try:
                        from webdriver_manager.chrome import ChromeDriverManager

                        drv = webdriver.Chrome(
                            service=Service(ChromeDriverManager().install()),
                            options=opts,
                        )
                    except Exception:
                        drv = webdriver.Chrome(options=opts)
            except Exception as exc:
                error_msg = str(exc)
                browser = ""

        if browser == "firefox" and drv is None:
            try:
                from selenium.webdriver.firefox.options import Options
                from selenium.webdriver.firefox.service import Service

                opts = Options()
                if headless:
                    opts.add_argument("--headless")
                cached = _find_cached_driver("geckodriver")
                if cached:
                    drv = webdriver.Firefox(service=Service(cached), options=opts)
                else:
                    try:
                        from webdriver_manager.firefox import GeckoDriverManager

                        drv = webdriver.Firefox(
                            service=Service(GeckoDriverManager().install()),
                            options=opts,
                        )
                    except Exception:
                        drv = webdriver.Firefox(options=opts)
            except Exception as exc:
                error_msg = str(exc)

        if drv is None:
            raise RuntimeError(
                "Could not start any supported browser.\n"
                f"Detail: {error_msg}"
            )

        _driver = drv
        return _driver


def close_driver():
    global _driver
    with _driver_lock:
        if _driver is not None:
            try:
                _driver.quit()
            except Exception as exc:
                app_log(f"[whatsapp_helper.close_driver] {exc}")
            finally:
                _driver = None
                _set_state(STATE_BROWSER_CLOSED, "WhatsApp browser closed")


atexit.register(close_driver)


def _js_click(drv, element):
    try:
        drv.execute_script("arguments[0].click();", element)
    except Exception:
        element.click()


def _find_visible_element(drv, selectors, timeout=0):
    end = time.time() + max(timeout, 0)
    while True:
        for selector in selectors:
            try:
                element = drv.find_element("css selector", selector)
                if element.is_displayed():
                    return element
            except Exception:
                pass
        if timeout <= 0 or time.time() >= end:
            break
        time.sleep(0.5)
    return None


def _find_element_by_script(drv, script: str):
    try:
        element = drv.execute_script(script)
        if element is not None:
            return element
    except Exception:
        pass
    return None


def _page_source_contains(drv, tokens) -> bool:
    try:
        page = (drv.page_source or "").lower()
    except Exception:
        return False
    return any(str(token).lower() in page for token in tokens)


def _find_existing_whatsapp_tab(drv):
    current = None
    try:
        current = drv.current_window_handle
    except Exception:
        current = None

    for handle in list(getattr(drv, "window_handles", [])):
        try:
            drv.switch_to.window(handle)
            if WA_BASE in (drv.current_url or ""):
                return handle
        except Exception:
            continue
    if current:
        try:
            drv.switch_to.window(current)
        except Exception:
            pass
    return None


def _ensure_whatsapp_tab(drv):
    existing = _find_existing_whatsapp_tab(drv)
    if existing:
        drv.switch_to.window(existing)
        return existing

    try:
        handle = drv.current_window_handle
    except Exception:
        handle = None

    if handle:
        drv.get(WA_BASE)
        return handle

    drv.get(WA_BASE)
    return drv.current_window_handle


def _logged_in_now(drv) -> bool:
    ready_selectors = [
        "[data-testid='chat-list']",
        "[data-testid='default-user']",
        "[data-testid='chat-list-search']",
        "div#pane-side",
        "div[aria-label='Chat list']",
        "div[aria-label='Chats']",
        "div[aria-label='Search input textbox']",
        "div[aria-label='Search or start a new chat']",
        "div[role='textbox'][aria-label*='Search']",
        "button[aria-label='New chat']",
        "span[data-icon='new-chat-outline']",
        "span[data-icon='new-chat']",
        "div[role='navigation']",
    ]
    if _find_visible_element(drv, ready_selectors, timeout=0) is not None:
        return True

    return _page_source_contains(
        drv,
        (
            "search or start a new chat",
            "whatsapp business on web",
            'aria-label="chat list"',
            'aria-label="chats"',
            'id="pane-side"',
        ),
    )


def _qr_visible_now(drv) -> bool:
    qr_selectors = [
        "canvas[aria-label*='QR']",
        "canvas[aria-label*='Scan']",
        "div[data-testid='qrcode']",
        "canvas",
    ]
    element = _find_visible_element(drv, qr_selectors, timeout=0)
    if element is None:
        return False
    page = (drv.page_source or "").lower()
    return "qr" in page or "scan" in page


def _wait_for_login(drv, wait_for_login: int) -> bool:
    deadline = time.time() + max(wait_for_login, 0)
    _set_state(STATE_WAITING_FOR_LOGIN, "Waiting for WhatsApp login (scan QR)...")
    while time.time() < deadline:
        if _logged_in_now(drv):
            _set_state(STATE_READY, "WhatsApp connected")
            return True
        time.sleep(1.0)
    if _logged_in_now(drv):
        _set_state(STATE_READY, "WhatsApp connected")
        return True
    _set_state(
        STATE_WAITING_FOR_LOGIN,
        "WhatsApp login pending - scan QR in browser",
    )
    return False


def ensure_session_ready(wait_for_login: int = 0) -> dict:
    try:
        drv = _get_driver()
        _set_state(STATE_OPENING_WHATSAPP, "Opening WhatsApp Web...")
        _ensure_whatsapp_tab(drv)
        if WA_BASE not in (drv.current_url or ""):
            drv.get(WA_BASE)
        deadline = time.time() + 6.0
        while time.time() < deadline:
            if _logged_in_now(drv):
                _set_state(STATE_READY, "WhatsApp connected")
                return {"ready": True, **get_session_snapshot()}

            if _qr_visible_now(drv):
                if wait_for_login > 0:
                    ready = _wait_for_login(drv, wait_for_login)
                    return {"ready": ready, **get_session_snapshot()}
                _set_state(STATE_WAITING_FOR_LOGIN, "Scan QR to connect WhatsApp")
                return {"ready": False, **get_session_snapshot()}

            time.sleep(0.5)

        if wait_for_login > 0:
            ready = _wait_for_login(drv, wait_for_login)
            return {"ready": ready, **get_session_snapshot()}

        _set_state(STATE_OPENING_WHATSAPP, "Opening WhatsApp Web...")
        return {"ready": False, **get_session_snapshot()}
    except Exception as exc:
        _set_state(STATE_FAILED, "Could not start WhatsApp", str(exc))
        return {"ready": False, **get_session_snapshot()}


def check_login_status(timeout: int = 20) -> str:
    snapshot = ensure_session_ready(wait_for_login=max(timeout, 0))
    if snapshot["state"] == STATE_READY:
        return "logged_in"
    if snapshot["state"] == STATE_WAITING_FOR_LOGIN:
        return "logged_out"
    if snapshot["state"] in (STATE_OPENING_WHATSAPP, STATE_STARTING_BROWSER):
        return "loading"
    if snapshot["state"] == STATE_BROWSER_CLOSED:
        return "browser_closed"
    if snapshot["state"] == STATE_FAILED:
        return f"error: {snapshot.get('last_error', snapshot.get('message', 'Unknown error'))}"
    return "loading"


def is_logged_in(timeout: int = 20) -> bool:
    return check_login_status(timeout) == "logged_in"


def open_whatsapp_web(wait_for_login: int = 0):
    snapshot = ensure_session_ready(wait_for_login=wait_for_login)
    if snapshot.get("state") == STATE_FAILED:
        _open_default_browser(WA_BASE)
        return None
    try:
        return _get_driver()
    except Exception:
        _open_default_browser(WA_BASE)
        return None


def _message_url(phone: str, message: str) -> str:
    cc = _get_country_code()
    encoded = urllib.parse.quote(message)
    return f"{WA_BASE}/send?phone={cc}{phone}&text={encoded}"


def _open_default_browser(url: str) -> bool:
    try:
        # new=0 asks the OS/default browser to reuse an existing browser window
        # when possible. Edge/Chrome may still choose a new tab, but we should
        # not force that from the app.
        if webbrowser.open(url, new=0, autoraise=True):
            return True
    except Exception:
        pass
    try:
        os.startfile(url)  # type: ignore[attr-defined]
        return True
    except Exception as exc:
        _set_state(STATE_FAILED, "Could not open default browser", str(exc))
        return False


def open_default_whatsapp_web() -> bool:
    """Open WhatsApp Web in the OS default browser when automation is unavailable."""
    if _open_default_browser(WA_BASE):
        _set_state(
            STATE_DEFAULT_BROWSER_OPEN,
            "WhatsApp Web opened in default browser",
        )
        return True
    return False


def _open_message_in_default_browser(phone: str, message: str) -> bool:
    if _open_default_browser(_message_url(phone, message)):
        _set_state(
            STATE_WAITING_MANUAL_SEND,
            "WhatsApp opened in default browser - manual Send required",
        )
        return True
    return False


def _send_button(drv, timeout=10):
    selectors = [
        "div[data-testid='send-btn']",
        "button[data-testid='compose-btn-send']",
        "button[data-testid='send']",
        "span[data-icon='send']",
        "span[data-icon*='send']",
        "button span[data-icon*='send']",
        "button[aria-label*='Send']",
        "button[aria-label*='send']",
        "div[aria-label*='Send']",
        "div[aria-label*='send']",
    ]
    element = _find_visible_element(drv, selectors, timeout=timeout)
    if element is not None:
        return element

    return _find_element_by_script(
        drv,
        """
        const root = document.querySelector("footer") || document;
        const all = Array.from(root.querySelectorAll(
          "button, div[role='button'], span[data-icon], div[aria-label]"
        ));
        return all.find((el) => {
          const label = [
            el.getAttribute("aria-label"),
            el.getAttribute("title"),
            el.getAttribute("data-testid"),
            el.getAttribute("data-icon"),
            el.textContent
          ].filter(Boolean).join(" ").toLowerCase();
          return label.includes("send") || !!el.querySelector("span[data-icon*='send']");
        }) || null;
        """,
    )


def _compose_box(drv, timeout=0):
    selectors = [
        "div[data-testid='conversation-compose-box-input']",
        "div[role='textbox'][aria-label*='Type a message']",
        "div[role='textbox'][aria-label*='Message']",
        "div[aria-label='Type a message'][contenteditable='true']",
        "footer div[contenteditable='true']",
        "div[contenteditable='true'][data-lexical-editor='true']",
        "div[role='textbox'][contenteditable='true']",
    ]
    return _find_visible_element(drv, selectors, timeout=timeout)


def _message_draft_present(drv) -> bool:
    try:
        return bool(
            drv.execute_script(
                """
                const boxes = Array.from(document.querySelectorAll(
                  "footer div[contenteditable='true'], div[role='textbox'][contenteditable='true'], div[contenteditable='true'][data-lexical-editor='true']"
                ));
                return boxes.some((box) => (box.innerText || box.textContent || "").trim().length > 0);
                """
            )
        )
    except Exception:
        return False


def _click_send_control(drv) -> bool:
    btn = _send_button(drv, timeout=2)
    if btn is not None:
        try:
            _js_click(drv, btn)
            return True
        except Exception:
            pass

    try:
        return bool(
            drv.execute_script(
                """
                const root = document.querySelector("footer") || document;
                const all = Array.from(root.querySelectorAll(
                  "button, div[role='button'], span[data-icon], div[aria-label]"
                ));
                const target = all.find((el) => {
                  const label = [
                    el.getAttribute("aria-label"),
                    el.getAttribute("title"),
                    el.getAttribute("data-testid"),
                    el.getAttribute("data-icon"),
                    el.textContent
                  ].filter(Boolean).join(" ").toLowerCase();
                  return label.includes("send") || !!el.querySelector("span[data-icon*='send']");
                });
                if (!target) return false;
                const clickable = target.closest("button, div[role='button']") || target;
                clickable.click();
                return true;
                """
            )
        )
    except Exception:
        return False


def _press_enter_to_send(drv) -> bool:
    box = _compose_box(drv, timeout=2)
    if box is None:
        return False
    try:
        _js_click(drv, box)
    except Exception:
        pass
    try:
        from selenium.webdriver.common.keys import Keys

        box.send_keys(Keys.ENTER)
        return True
    except Exception:
        try:
            drv.execute_script(
                """
                const box = arguments[0];
                box.dispatchEvent(new KeyboardEvent("keydown", {
                  key: "Enter", code: "Enter", keyCode: 13, which: 13,
                  bubbles: true, cancelable: true
                }));
                """,
                box,
            )
            return True
        except Exception:
            return False


def _compose_ready(drv, timeout=20) -> bool:
    compose_selectors = [
        "div[data-testid='conversation-compose-box-input']",
        "div[role='textbox'][contenteditable='true']",
        "div[role='textbox'][aria-label*='Type a message']",
        "div[role='textbox'][aria-label*='Message']",
        "div[aria-label='Type a message'][contenteditable='true']",
        "div[contenteditable='true'][data-lexical-editor='true']",
        "footer div[contenteditable='true']",
    ]
    end = time.time() + timeout
    while time.time() < end:
        if _find_visible_element(drv, compose_selectors, timeout=0):
            return True
        if _send_button(drv, timeout=0):
            return True
        try:
            if drv.execute_script(
                """
                return !!document.querySelector(
                  "footer div[contenteditable='true'], div[role='textbox'][contenteditable='true'], div[contenteditable='true'][data-lexical-editor='true']"
                );
                """
            ):
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _wait_manual_or_auto_send(drv, manual_send_timeout: int, auto_send_fallback: bool) -> bool:
    button_seen = False
    deadline = time.time() + max(manual_send_timeout, 0)
    if manual_send_timeout > 0:
        _set_state(STATE_WAITING_MANUAL_SEND, "Waiting for manual WhatsApp send...")
        while time.time() < deadline:
            btn = _send_button(drv, timeout=0)
            if btn is not None:
                button_seen = True
            elif button_seen:
                _set_state(STATE_SENT, "WhatsApp message sent")
                return True
            time.sleep(1.0)

    if not auto_send_fallback:
        _set_state(STATE_FAILED, "Manual send not completed", "Send button still visible")
        return False

    if _send_button(drv, timeout=5) is None:
        if button_seen or not _message_draft_present(drv):
            _set_state(STATE_SENT, "WhatsApp message sent")
            return True
        _set_state(STATE_FAILED, "Could not find send button", "Message composer not ready")
        return False

    _set_state(STATE_AUTO_SENDING, "Auto sending WhatsApp message...")
    if not _click_send_control(drv):
        _set_state(STATE_FAILED, "Auto send failed", "Could not click send control")
        return False

    quick_end = time.time() + 2
    while time.time() < quick_end:
        if not _message_draft_present(drv):
            _set_state(STATE_SENT, "WhatsApp message sent")
            return True
        time.sleep(0.25)

    _press_enter_to_send(drv)

    end = time.time() + 10
    while time.time() < end:
        if _send_button(drv, timeout=0) is None or not _message_draft_present(drv):
            _set_state(STATE_SENT, "WhatsApp message sent")
            return True
        time.sleep(0.5)

    _set_state(STATE_FAILED, "Message send not confirmed", "Send button still visible after auto send")
    return False


def send_text(phone: str, message: str, wait_for_login: int = 45,
              manual_send_timeout: int = 10, auto_send_fallback: bool = True) -> bool:
    if not validate_phone(str(phone)):
        _set_state(STATE_FAILED, "Invalid phone number", str(phone))
        return False
    try:
        session = ensure_session_ready(wait_for_login=wait_for_login)
        if not session.get("ready"):
            if session.get("state") != STATE_WAITING_FOR_LOGIN:
                _open_message_in_default_browser(phone, message)
            return False
        drv = _get_driver()
        _ensure_whatsapp_tab(drv)
        _set_state(STATE_OPENING_CHAT, "Opening WhatsApp chat...")
        drv.get(_message_url(phone, message))
        if not _compose_ready(drv, timeout=wait_for_login):
            _set_state(STATE_FAILED, "Chat did not open", "Composer was not ready")
            return False
        return _wait_manual_or_auto_send(drv, manual_send_timeout, auto_send_fallback)
    except Exception as exc:
        if _open_message_in_default_browser(phone, message):
            return False
        _set_state(STATE_FAILED, "WhatsApp send failed", str(exc))
        return False


def send_image(phone: str, image_path: str, caption: str = "",
               wait_for_login: int = 45, manual_send_timeout: int = 0,
               auto_send_fallback: bool = True) -> bool:
    if not os.path.exists(image_path):
        return send_text(phone, caption, wait_for_login, manual_send_timeout, auto_send_fallback)
    if not validate_phone(str(phone)):
        _set_state(STATE_FAILED, "Invalid phone number", str(phone))
        return False
    try:
        session = ensure_session_ready(wait_for_login=wait_for_login)
        if not session.get("ready"):
            return False

        drv = _get_driver()
        _ensure_whatsapp_tab(drv)
        _set_state(STATE_OPENING_CHAT, "Opening WhatsApp chat...")
        drv.get(f"{WA_BASE}/send?phone={_get_country_code()}{phone}")
        if not _compose_ready(drv, timeout=wait_for_login):
            _set_state(STATE_FAILED, "Chat did not open", "Composer was not ready")
            return False

        attach_selectors = [
            "div[data-testid='attach-btn']",
            "span[data-icon='attach']",
            "button[aria-label*='Attach']",
            "div[aria-label*='Attach']",
            "span[data-icon='clip']",
            "div[title='Attach']",
        ]
        attach = _find_visible_element(drv, attach_selectors, timeout=10)
        if attach is None:
            _set_state(STATE_FAILED, "Attach button not found", "Could not attach image")
            return False
        _js_click(drv, attach)
        time.sleep(1.0)

        file_sent = False
        for input_el in drv.find_elements("css selector", "input[type='file']"):
            try:
                drv.execute_script(
                    "arguments[0].style.display='block';"
                    "arguments[0].style.visibility='visible';"
                    "arguments[0].style.opacity='1';",
                    input_el,
                )
                input_el.send_keys(os.path.abspath(image_path))
                file_sent = True
                break
            except Exception:
                continue

        if not file_sent:
            _set_state(STATE_FAILED, "Image attach failed", "No usable file input found")
            return False

        time.sleep(2.0)
        if caption:
            caption_selectors = [
                "div[data-testid='media-caption-input-container'] div[contenteditable='true']",
                "div[class*='caption'] div[contenteditable='true']",
                "div[data-testid='media-caption-input']",
                "div[contenteditable='true'][data-tab='7']",
            ]
            caption_box = _find_visible_element(drv, caption_selectors, timeout=8)
            if caption_box is not None:
                try:
                    _js_click(drv, caption_box)
                    caption_box.send_keys(caption)
                except Exception:
                    pass

        return _wait_manual_or_auto_send(drv, manual_send_timeout, auto_send_fallback)
    except Exception as exc:
        _set_state(STATE_FAILED, "WhatsApp image send failed", str(exc))
        return False


def bulk_send(recipients: list, message_template: str, image_path: str = "",
              delay: int = 8, progress_cb=None, done_cb=None):
    def _worker():
        sent = 0
        fail = 0
        total = len(recipients)

        session = ensure_session_ready(wait_for_login=45)
        if not session.get("ready"):
            if done_cb:
                done_cb(
                    0,
                    total,
                    session.get("message", "WhatsApp is not ready"),
                )
            return

        for index, (name, phone) in enumerate(recipients, start=1):
            if not validate_phone(str(phone)):
                fail += 1
                app_log(f"[bulk_send] skipped invalid phone: {phone}")
                continue
            if progress_cb:
                progress_cb(index, total, name)
            msg = message_template.replace("{name}", name)
            try:
                if image_path and os.path.exists(image_path):
                    ok = send_image(
                        phone,
                        image_path,
                        msg,
                        wait_for_login=10,
                        manual_send_timeout=0,
                        auto_send_fallback=True,
                    )
                else:
                    ok = send_text(
                        phone,
                        msg,
                        wait_for_login=10,
                        manual_send_timeout=0,
                        auto_send_fallback=True,
                    )
                if ok:
                    sent += 1
                else:
                    fail += 1
            except Exception as exc:
                app_log(f"[bulk_send] {phone}: {exc}")
                fail += 1
            time.sleep(max(delay, 1))

        if done_cb:
            done_cb(sent, fail, "")

    threading.Thread(target=_worker, daemon=True).start()


__all__ = [
    "STATE_NOT_STARTED",
    "STATE_STARTING_BROWSER",
    "STATE_OPENING_WHATSAPP",
    "STATE_WAITING_FOR_LOGIN",
    "STATE_READY",
    "STATE_DEFAULT_BROWSER_OPEN",
    "STATE_OPENING_CHAT",
    "STATE_WAITING_MANUAL_SEND",
    "STATE_AUTO_SENDING",
    "STATE_SENT",
    "STATE_FAILED",
    "STATE_BROWSER_CLOSED",
    "ensure_session_ready",
    "get_session_snapshot",
    "check_login_status",
    "is_logged_in",
    "open_whatsapp_web",
    "open_default_whatsapp_web",
    "send_text",
    "send_image",
    "bulk_send",
    "close_driver",
]
