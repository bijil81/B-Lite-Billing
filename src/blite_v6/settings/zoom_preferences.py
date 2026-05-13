from __future__ import annotations

from typing import Mapping


GLOBAL_ZOOM_MIN = 0.85
GLOBAL_ZOOM_MAX = 1.25
GLOBAL_ZOOM_STEP = 0.05
GLOBAL_ZOOM_DEFAULT = 1.0

BILLING_WORKFLOW_ZOOM_OPTIONS = ("fit", "compact", "normal", "comfortable")
BILLING_WORKFLOW_ZOOM_DEFAULT = "fit"
BILLING_WORKFLOW_ZOOM_LABELS = {
    "fit": "Fit Screen",
    "compact": "Compact 90%",
    "normal": "Normal 100%",
    "comfortable": "Comfortable 110%",
}
BILLING_WORKFLOW_ZOOM_FROM_LABEL = {
    label: key for key, label in BILLING_WORKFLOW_ZOOM_LABELS.items()
}


def clamp_global_zoom(value: object) -> float:
    try:
        zoom = float(value)
    except Exception:
        zoom = GLOBAL_ZOOM_DEFAULT
    zoom = max(GLOBAL_ZOOM_MIN, min(GLOBAL_ZOOM_MAX, zoom))
    return round(zoom, 2)


def step_global_zoom(value: object, direction: int) -> float:
    zoom = clamp_global_zoom(value)
    direction = 1 if direction > 0 else -1 if direction < 0 else 0
    if direction == 0:
        return zoom
    return clamp_global_zoom(zoom + (GLOBAL_ZOOM_STEP * direction))


def normalize_billing_workflow_zoom(value: object) -> str:
    text = str(value or "").strip()
    if text in BILLING_WORKFLOW_ZOOM_OPTIONS:
        return text
    return BILLING_WORKFLOW_ZOOM_FROM_LABEL.get(text, BILLING_WORKFLOW_ZOOM_DEFAULT)


def billing_workflow_zoom_label(value: object) -> str:
    return BILLING_WORKFLOW_ZOOM_LABELS[normalize_billing_workflow_zoom(value)]


def billing_workflow_zoom_factor(value: object, *, screen_height: int | None = None) -> float:
    mode = normalize_billing_workflow_zoom(value)
    if mode == "compact":
        return 0.90
    if mode == "normal":
        return 1.0
    if mode == "comfortable":
        return 1.10
    height = int(screen_height or 0)
    if height and height <= 820:
        return 0.84
    if height and height <= 1080:
        return 0.88
    return 0.94


def build_zoom_preferences_payload(
    current_settings: Mapping,
    *,
    ui_scale: object,
    billing_workflow_zoom: object,
) -> dict:
    cfg = dict(current_settings)
    cfg["ui_scale"] = clamp_global_zoom(ui_scale)
    cfg["billing_workflow_zoom"] = normalize_billing_workflow_zoom(billing_workflow_zoom)
    return cfg
