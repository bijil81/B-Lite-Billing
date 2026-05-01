from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class LogoSectionView:
    frame_pady: int
    fallback_font_size: int
    max_logo_width: int


@dataclass(frozen=True)
class UserSectionView:
    name: str
    avatar_initial: str
    role_text: str
    role_color_key: str
    logout_width: int
    logout_height: int
    logout_font_size: int


@dataclass(frozen=True)
class ActionButtonSpec:
    key: str
    text: str
    icon_key: str
    command_name: str
    color_key: str
    hover_color: str
    width: int
    height: int
    radius: int
    font_size: int


def logo_section_view(compact: bool, sidebar_width: int) -> LogoSectionView:
    return LogoSectionView(
        frame_pady=12 if compact else 16,
        fallback_font_size=12 if compact else 13,
        max_logo_width=min(148 if not compact else 122, sidebar_width - 20),
    )


def user_section_view(
    user: Mapping[str, object],
    nav_font_size: int,
    sidebar_button_height: int,
    user_button_width: int,
) -> UserSectionView:
    name = str(user.get("name", "U") or "U")
    role_text = str(user.get("role", "staff") or "staff").upper()
    role_color_key = "accent" if role_text == "OWNER" else "blue"
    return UserSectionView(
        name=name,
        avatar_initial=name[0].upper() if name else "U",
        role_text=role_text,
        role_color_key=role_color_key,
        logout_width=user_button_width,
        logout_height=sidebar_button_height,
        logout_font_size=max(9, nav_font_size - 1),
    )


def topbar_action_button_specs(is_owner: bool) -> tuple[ActionButtonSpec, ...]:
    specs: list[ActionButtonSpec] = []
    if is_owner:
        specs.append(
            ActionButtonSpec(
                key="admin",
                text="Admin",
                icon_key="admin",
                command_name="_open_admin",
                color_key="red",
                hover_color="#c0392b",
                width=100,
                height=30,
                radius=8,
                font_size=10,
            )
        )
    specs.extend(
        (
            ActionButtonSpec(
                key="help",
                text="Help",
                icon_key="help",
                command_name="_show_context_help",
                color_key="blue",
                hover_color="#154360",
                width=90,
                height=30,
                radius=8,
                font_size=10,
            ),
            ActionButtonSpec(
                key="alerts",
                text="Notifications",
                icon_key="alerts",
                command_name="_show_notifications",
                color_key="#D4A017",
                hover_color="#C58F00",
                width=160,
                height=30,
                radius=8,
                font_size=10,
            ),
        )
    )
    return tuple(specs)
