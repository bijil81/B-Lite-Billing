from src.blite_v6.app.dpi_runtime import dpi_snapshot_changed, tk_scaling_for_dpi


def test_tk_scaling_for_dpi_matches_windows_scale_levels():
    assert round(tk_scaling_for_dpi(96), 4) == 1.3333
    assert round(tk_scaling_for_dpi(120), 4) == 1.6667
    assert round(tk_scaling_for_dpi(144), 4) == 2.0


def test_dpi_snapshot_changed_detects_scale_and_screen_changes():
    previous = {"dpi": 96.0, "screen_w": 1920, "screen_h": 1080}
    assert dpi_snapshot_changed(previous, {"dpi": 120.0, "screen_w": 1920, "screen_h": 1080})
    assert dpi_snapshot_changed(previous, {"dpi": 96.0, "screen_w": 1536, "screen_h": 864})
    assert not dpi_snapshot_changed(previous, {"dpi": 96.4, "screen_w": 1920, "screen_h": 1080})
