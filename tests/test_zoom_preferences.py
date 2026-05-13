from src.blite_v6.settings.zoom_preferences import (
    billing_workflow_zoom_factor,
    billing_workflow_zoom_label,
    build_zoom_preferences_payload,
    clamp_global_zoom,
    normalize_billing_workflow_zoom,
    step_global_zoom,
)


def test_global_zoom_clamps_and_steps():
    assert clamp_global_zoom("bad") == 1.0
    assert clamp_global_zoom(0.2) == 0.85
    assert clamp_global_zoom(2.0) == 1.25
    assert step_global_zoom(1.0, 1) == 1.05
    assert step_global_zoom(1.0, -1) == 0.95


def test_billing_workflow_zoom_normalization_and_factor():
    assert normalize_billing_workflow_zoom("Compact 90%") == "compact"
    assert normalize_billing_workflow_zoom("unknown") == "fit"
    assert billing_workflow_zoom_label("comfortable") == "Comfortable 110%"
    assert billing_workflow_zoom_factor("normal", screen_height=1080) == 1.0
    assert billing_workflow_zoom_factor("comfortable", screen_height=1080) == 1.10
    assert billing_workflow_zoom_factor("fit", screen_height=1080) < 1.0


def test_zoom_preferences_payload_preserves_existing_settings():
    result = build_zoom_preferences_payload(
        {"salon_name": "Demo"},
        ui_scale=1.3,
        billing_workflow_zoom="Normal 100%",
    )
    assert result["salon_name"] == "Demo"
    assert result["ui_scale"] == 1.25
    assert result["billing_workflow_zoom"] == "normal"
