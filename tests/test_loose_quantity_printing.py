from __future__ import annotations

from print_utils import build_item_line_58mm, build_item_line_80mm, build_item_line_a4


def test_thermal_item_lines_keep_decimal_quantity_label_and_amount():
    line_58 = build_item_line_58mm(1, "Rice Loose", 1.24, 60.0, 32, True, "1.24 kg")
    line_80 = build_item_line_80mm(1, "Rice Loose", 1.24, 60.0, 42, True, "1.24 kg")
    line_a4 = build_item_line_a4(1, "Rice Loose", 1.24, 60.0, 80, True, "1.24 kg")

    assert "1.24 kg" in "\n".join(line_58)
    assert "74.40" in "\n".join(line_58)
    assert "1.24 kg" in line_80
    assert "74.40" in line_80
    assert "1.24 kg" in line_a4
    assert "74.40" in line_a4
