from __future__ import annotations

from dataclasses import dataclass

SPLASH_MIN_DURATION_SECONDS = 2.2
SPLASH_MAX_FRAMES = 12
SPLASH_MEDIA_FIRST_DELAY_MS = 50
LOADING_PULSE_FIRST_DELAY_MS = 30
LOADING_TEXT_FIRST_DELAY_MS = 40
LOADING_PULSE_REPEAT_MS = 220
LOADING_TEXT_REPEAT_MS = 320
MEDIA_FRAME_REPEAT_MS = 70
STARTUP_LOGO_FIRST_DELAY_MS = 60
STARTUP_LOGO_REPEAT_MS = 110
PAGE_TITLE_REVEAL_MS = 140
TODAY_REVEAL_MS = 150


@dataclass(frozen=True)
class GifSamplingPlan:
    max_frames: int
    step: int


GIFSamplingPlan = GifSamplingPlan


def splash_finish_delay_ms(
    animations_enabled: bool,
    started_at: float,
    now: float,
    min_duration: float = SPLASH_MIN_DURATION_SECONDS,
) -> int | None:
    if not animations_enabled:
        return None
    remaining = min_duration - (now - started_at)
    if remaining <= 0:
        return None
    return max(1, int(remaining * 1000))


def gif_sampling_plan(total_frames: int | None, max_frames: int = SPLASH_MAX_FRAMES) -> GifSamplingPlan:
    frame_count = max(1, int(total_frames or 1))
    safe_max = max(1, int(max_frames))
    return GifSamplingPlan(max_frames=safe_max, step=max(1, frame_count // safe_max))


def splash_static_logo_size(image_size: tuple[int, int]) -> tuple[int, int]:
    image_w, image_h = image_size
    width = min(360, max(1, image_w))
    height = max(1, int(max(1, image_h) * width / max(1, image_w)))
    return width, height


def placeholder_logo_size(
    image_size: tuple[int, int],
    screen_size: tuple[int, int],
) -> tuple[int, int]:
    image_w, image_h = image_size
    screen_w, screen_h = screen_size
    target_w = max(260, int(max(1, screen_w) * 0.24))
    target_h_cap = max(140, int(max(1, screen_h) * 0.20))
    width = min(target_w, max(1, image_w), 480)
    height = max(1, int(max(1, image_h) * width / max(1, image_w)))
    if height > target_h_cap:
        height = target_h_cap
        width = max(1, int(max(1, image_w) * height / max(1, image_h)))
    return width, height


def loading_text_for_step(step: int) -> str:
    dots = "." * ((step % 3) + 1)
    return f"Loading{dots}"


def startup_logo_scale(step: int) -> float:
    scales = (0.88, 0.94, 1.00, 1.06, 1.12, 1.06, 1.00, 0.94)
    return scales[step % len(scales)]


def scaled_size(image_size: tuple[int, int], scale: float) -> tuple[int, int]:
    image_w, image_h = image_size
    return max(1, int(max(1, image_w) * scale)), max(1, int(max(1, image_h) * scale))
