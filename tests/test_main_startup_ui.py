from __future__ import annotations

from src.blite_v6.app.startup_ui import (
    GIFSamplingPlan,
    LOADING_PULSE_REPEAT_MS,
    LOADING_TEXT_REPEAT_MS,
    MEDIA_FRAME_REPEAT_MS,
    PAGE_TITLE_REVEAL_MS,
    STARTUP_LOGO_REPEAT_MS,
    TODAY_REVEAL_MS,
    gif_sampling_plan,
    loading_text_for_step,
    placeholder_logo_size,
    scaled_size,
    splash_finish_delay_ms,
    splash_static_logo_size,
    startup_logo_scale,
)


def test_splash_finish_delay_preserves_minimum_duration():
    assert splash_finish_delay_ms(True, started_at=10.0, now=10.5) == 1700
    assert splash_finish_delay_ms(True, started_at=10.0, now=12.3) is None
    assert splash_finish_delay_ms(False, started_at=10.0, now=10.5) is None


def test_gif_sampling_plan_limits_frames_like_legacy():
    assert gif_sampling_plan(60) == GIFSamplingPlan(max_frames=12, step=5)
    assert gif_sampling_plan(5) == GIFSamplingPlan(max_frames=12, step=1)
    assert gif_sampling_plan(None) == GIFSamplingPlan(max_frames=12, step=1)


def test_logo_size_helpers_preserve_aspect_ratio_and_caps():
    assert splash_static_logo_size((720, 360)) == (360, 180)
    assert splash_static_logo_size((200, 100)) == (200, 100)
    assert placeholder_logo_size((1000, 500), (1920, 1080)) == (432, 216)
    assert placeholder_logo_size((1000, 1000), (800, 600)) == (140, 140)


def test_loading_text_and_logo_scale_sequence():
    assert [loading_text_for_step(i) for i in range(4)] == [
        "Loading.",
        "Loading..",
        "Loading...",
        "Loading.",
    ]
    assert startup_logo_scale(0) == 0.88
    assert startup_logo_scale(4) == 1.12
    assert startup_logo_scale(8) == 0.88
    assert scaled_size((100, 50), 1.12) == (112, 56)


def test_animation_timer_constants_remain_stable():
    assert LOADING_PULSE_REPEAT_MS == 220
    assert LOADING_TEXT_REPEAT_MS == 320
    assert MEDIA_FRAME_REPEAT_MS == 70
    assert STARTUP_LOGO_REPEAT_MS == 110
    assert PAGE_TITLE_REVEAL_MS == 140
    assert TODAY_REVEAL_MS == 150
