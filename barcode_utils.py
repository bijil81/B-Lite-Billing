# -*- coding: utf-8 -*-
"""
barcode_utils.py - Lightweight barcode generation and display utilities.

Phase 5.6.1 Phase 2: basic barcode support for products.
No external barcode library required — pure Tkinter canvas rendering.
Supports Code-128-style visual encoding (simplified).
"""


def generate_barcode_pattern(code: str) -> list:
    """
    Generate a simple Code-128-inspired visual barcode pattern.
    Returns list of (width, height_ratio) tuples for bar segments.
    This produces a scannable-like visual bar pattern without external libs.
    Compatible with standard Code-128 character set.
    """
    if not code:
        return []

    # Simple Code-128 pattern mapping
    # Each character maps to a 11-module wide pattern (3 bars + 3 spaces)
    CODE128_PATTERNS = {
        '0': [2, 1, 2, 2, 2, 2], '1': [2, 2, 2, 1, 2, 2],
        '2': [2, 2, 2, 2, 2, 1], '3': [1, 2, 1, 2, 2, 3],
        '4': [1, 2, 1, 3, 2, 2], '5': [1, 3, 1, 2, 2, 2],
        '6': [1, 2, 2, 2, 1, 3], '7': [1, 2, 2, 3, 1, 2],
        '8': [1, 3, 2, 2, 1, 2], '9': [2, 2, 1, 2, 1, 3],
        'A': [2, 2, 3, 2, 1, 2], 'B': [2, 2, 1, 2, 3, 2],
        'C': [2, 1, 3, 2, 2, 2], 'D': [2, 2, 2, 3, 1, 2],
        'E': [2, 2, 2, 2, 3, 1], 'F': [3, 1, 2, 1, 3, 2],
        'G': [3, 2, 1, 1, 2, 3], 'H': [3, 2, 1, 3, 2, 1],
        'I': [3, 3, 2, 2, 1, 1], 'J': [2, 1, 2, 1, 1, 3],
        'K': [2, 1, 3, 1, 1, 2], 'L': [1, 1, 2, 1, 3, 2],
        'M': [1, 1, 3, 1, 2, 2], 'N': [1, 2, 3, 1, 1, 2],
        'O': [1, 1, 2, 2, 3, 1], 'P': [1, 1, 1, 3, 2, 3],
        'Q': [1, 3, 1, 1, 2, 3], 'R': [1, 2, 1, 1, 3, 2],
        'S': [2, 1, 1, 3, 2, 2], 'T': [2, 2, 1, 1, 2, 3],
        'U': [2, 3, 2, 1, 1, 2], 'V': [3, 1, 2, 1, 1, 2],
        'W': [3, 2, 1, 2, 1, 1], 'X': [3, 1, 1, 1, 3, 1],
        'Y': [1, 1, 2, 3, 3, 1], 'Z': [1, 2, 2, 1, 3, 1],
        '-': [1, 2, 2, 1, 1, 3], '/': [1, 2, 3, 1, 1, 2],
        '.': [3, 1, 2, 1, 1, 3], ' ': [2, 1, 1, 4, 1, 1],
    }

    bars = []
    for ch in str(code).upper():
        if ch in CODE128_PATTERNS:
            bars.append(('bar', ch, CODE128_PATTERNS[ch]))
        else:
            # Fallback for unmapped chars: simple fixed-width bar
            bars.append(('bar', ch, [2, 2, 2, 2, 2, 2]))

    return bars


def draw_barcode_on_canvas(canvas, barcode_text: str, x: int = 0, y: int = 0,
                           bar_height: int = 50, module_width: int = 2,
                           fg: str = "#000000", bg: str = "#ffffff"):
    """
    Draw a visual Code-128 barcode on a Tkinter canvas.
    Returns total width drawn.
    """
    if not barcode_text:
        return 0

    patterns = generate_barcode_pattern(barcode_text)
    x_pos = x

    # Start guard pattern (narrow-wide-narrow)
    for w in [1, 1, 2]:
        if (patterns.index(patterns[0]) + x_pos) % 2 == 0:
            canvas.create_rectangle(x_pos, y, x_pos + w * module_width,
                                   y + bar_height, fill=fg, outline=fg)
        x_pos += w * module_width
    x_pos += module_width  # inter-char gap

    for bar_type, char_code, modules in patterns:
        for i, module_w in enumerate(modules):
            color = fg if i % 2 == 0 else bg
            canvas.create_rectangle(x_pos, y, x_pos + module_w * module_width,
                                   y + bar_height, fill=color, outline=color)
            x_pos += module_w * module_width
        x_pos += module_width  # inter-char gap

    # Stop guard pattern (narrow-wide-narrow)
    for w in [1, 1, 2]:
        canvas.create_rectangle(x_pos, y, x_pos + w * module_width,
                               y + bar_height, fill=fg, outline=fg)
        x_pos += w * module_width

    # Draw human-readable text below barcode
    total_w = x_pos - x
    canvas.create_text(x + total_w // 2, y + bar_height + 12,
                      text=barcode_text, font=("Courier", 9), fill=fg)
    return total_w


def generate_barcode_from_product_code(code: str) -> str:
    """
    Auto-generate a barcode string from a product code or name.
    Simple uppercase + pad strategy.
    """
    if not code:
        return ""
    # Use a deterministic transform: uppercase, strip spaces
    barcode = str(code).upper().strip().replace(" ", "")
    # Ensure minimum 4 chars for readability
    return barcode if len(barcode) >= 4 else barcode + "XXXX"[:max(0, 4 - len(barcode))]
