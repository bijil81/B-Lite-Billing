from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


CLASSIFICATION_FIELDS = ("name", "base_product", "category", "hsn_sac", "sku", "barcode")
CLASSIFICATION_MODES = ("exact", "contains")


def _text(value: object, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _float_rate(value: object, default: float | None = None) -> float | None:
    try:
        rate = float(str(value).strip())
    except Exception:
        return default
    if rate < 0:
        return default
    return rate


def _normalize_field(value: object) -> str:
    field = _text(value).lower().replace(" ", "_").replace("-", "_")
    if field in {"product", "product_name", "item", "item_name", "name"}:
        return "name"
    if field in {"base", "base_product", "base_item"}:
        return "base_product"
    if field in {"cat", "category"}:
        return "category"
    if field in {"hsn", "hsn_sac", "hsn/sac", "sac"}:
        return "hsn_sac"
    if field in {"sku"}:
        return "sku"
    if field in {"barcode", "bar_code"}:
        return "barcode"
    if field == "any":
        return "name"
    return field


def _normalize_mode(value: object) -> str:
    mode = _text(value).lower().replace("-", "_")
    if mode in {"has", "contains", "contain", "keyword", "search"}:
        return "contains"
    return "exact"


def _match_texts(rule_field: str, product: Mapping[str, Any]) -> list[str]:
    if rule_field == "name":
        return [
            _text(product.get("name")),
            _text(product.get("bill_label")),
            _text(product.get("base_product")),
        ]
    if rule_field == "base_product":
        return [_text(product.get("base_product")), _text(product.get("name"))]
    if rule_field == "category":
        return [_text(product.get("category"))]
    if rule_field == "hsn_sac":
        return [_text(product.get("hsn_sac"))]
    if rule_field == "sku":
        return [_text(product.get("sku"))]
    if rule_field == "barcode":
        return [_text(product.get("barcode"))]
    return [_text(product.get("name"))]


def _contains(normalized_text: str, normalized_pattern: str) -> bool:
    return bool(normalized_text and normalized_pattern and normalized_pattern in normalized_text)


def normalize_gst_classification_rules(
    raw: Mapping[str, Any] | Iterable[Mapping[str, Any]] | None,
    *,
    fallback: Iterable[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    source = fallback or []
    rules: list[dict[str, Any]] = []

    def _append(entry: Mapping[str, Any]) -> None:
        field = _normalize_field(entry.get("field") or entry.get("match_on") or entry.get("target"))
        mode = _normalize_mode(entry.get("mode") or entry.get("match_type") or entry.get("kind"))
        pattern = _text(entry.get("pattern") or entry.get("value") or entry.get("text"))
        rate = _float_rate(entry.get("rate") if "rate" in entry else entry.get("gst_rate"), None)
        note = _text(entry.get("note"))
        if field not in CLASSIFICATION_FIELDS or not pattern or rate is None:
            return
        rules.append(
            {
                "field": field,
                "mode": mode,
                "pattern": pattern,
                "rate": round(float(rate), 2),
                "note": note,
            }
        )

    if raw is None:
        for entry in source:
            if isinstance(entry, Mapping):
                _append(entry)
        return rules

    if isinstance(raw, Mapping):
        for key, value in raw.items():
            if isinstance(value, Mapping):
                entry = dict(value)
                entry.setdefault("pattern", key)
                _append(entry)
            else:
                _append({"field": "name", "mode": "contains", "pattern": key, "rate": value})
        return rules

    for entry in raw:
        if isinstance(entry, Mapping):
            _append(entry)
    return rules


def gst_classification_rows(settings: Mapping[str, Any] | None) -> list[tuple[str, str, str, float]]:
    cfg = settings or {}
    raw = cfg.get("gst_classification_rules") if isinstance(cfg, Mapping) else None
    normalized = normalize_gst_classification_rules(raw)
    return [(rule["field"], rule["mode"], rule["pattern"], float(rule["rate"])) for rule in normalized]


def build_gst_classification_payload(
    current_settings: Mapping[str, Any],
    *,
    gst_classification_rules: Mapping[str, Any] | Iterable[Mapping[str, Any]] | None,
) -> dict:
    cfg = dict(current_settings)
    cfg["gst_classification_rules"] = normalize_gst_classification_rules(
        gst_classification_rules,
        fallback=current_settings.get("gst_classification_rules") if isinstance(current_settings, Mapping) else None,
    )
    return cfg


def gst_classification_saved_message(settings: Mapping[str, Any]) -> str:
    rows = gst_classification_rows(settings)
    if not rows:
        return "GST classification saved!\nNo specific item rules configured."
    preview = ", ".join(f"{field}:{pattern}={rate:g}%" for field, _mode, pattern, rate in rows[:4])
    if len(rows) > 4:
        preview += f", +{len(rows) - 4} more"
    return f"GST classification saved!\nRules: {len(rows)}\n{preview}"


def resolve_gst_classification_rate(
    product: Mapping[str, Any] | object,
    *,
    rules: Iterable[Mapping[str, Any]] | Mapping[str, Any] | None = None,
) -> float | None:
    if not isinstance(product, Mapping):
        return None

    normalized_rules = normalize_gst_classification_rules(rules)
    if not normalized_rules:
        return None

    product_map = dict(product)

    exact_matches: list[tuple[int, dict[str, Any]]] = []
    contains_matches: list[tuple[int, dict[str, Any]]] = []
    for index, rule in enumerate(normalized_rules):
        field = rule["field"]
        pattern = _text(rule["pattern"])
        if not pattern:
            continue
        candidates = _match_texts(field, product_map)
        for candidate in candidates:
            candidate_norm = _text(candidate).lower()
            pattern_norm = _text(pattern).lower()
            if rule["mode"] == "exact" and candidate_norm == pattern_norm:
                exact_matches.append((index, rule))
                break
            if rule["mode"] == "contains" and _contains(candidate_norm, pattern_norm):
                contains_matches.append((index, rule))
                break

    matches = exact_matches or contains_matches
    if not matches:
        return None
    return float(matches[0][1]["rate"])
