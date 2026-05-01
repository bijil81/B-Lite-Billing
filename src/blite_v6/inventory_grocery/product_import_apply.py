"""Apply validated product import previews to inventory and product catalog."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import os
from typing import Any, Callable, Mapping
from uuid import uuid4

from adapters.product_catalog_adapter import (
    create_product_with_variants_v5,
    refresh_product_catalog_cache,
)
from utils import DATA_DIR, app_log, load_json, save_json, today_str

from .product_import import ImportPreview, ImportPreviewRow


F_IMPORT_BATCHES = os.path.join(DATA_DIR, "inventory_import_batches.json")


@dataclass(frozen=True)
class ImportApplyRowResult:
    row_number: int
    action: str
    item_name: str
    status: str
    message: str = ""


@dataclass(frozen=True)
class ImportApplyResult:
    batch_id: str
    source_file: str
    rows: tuple[ImportApplyRowResult, ...]
    log_path: str = F_IMPORT_BATCHES

    @property
    def created_count(self) -> int:
        return sum(1 for row in self.rows if row.action == "create" and row.status == "applied")

    @property
    def updated_count(self) -> int:
        return sum(1 for row in self.rows if row.action == "update" and row.status == "applied")

    @property
    def skipped_count(self) -> int:
        return sum(1 for row in self.rows if row.status == "skipped")

    @property
    def error_count(self) -> int:
        return sum(1 for row in self.rows if row.status == "error")

    @property
    def applied_count(self) -> int:
        return self.created_count + self.updated_count

    @property
    def ok(self) -> bool:
        return self.applied_count > 0 and self.error_count == 0


def _text(value: object, default: str = "") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _matched_inventory_name(row: ImportPreviewRow) -> str:
    if ":" not in row.match_key:
        return ""
    return row.match_key.split(":", 1)[1].strip()


def _target_inventory_name(row: ImportPreviewRow) -> str:
    return _text(row.mapped.get("name") or row.inventory_item.get("bill_label"))


def _inventory_payload(item: Mapping[str, Any], imported_on: str) -> dict[str, Any]:
    payload = dict(item)
    payload["updated"] = imported_on
    return payload


def _row_error(row: ImportPreviewRow) -> str:
    messages = [issue.message for issue in row.errors]
    return "; ".join(messages) or "Row has validation errors"


def _append_batch_log(result: ImportApplyResult, *, log_path: str = F_IMPORT_BATCHES) -> None:
    rows = load_json(log_path, [])
    if not isinstance(rows, list):
        rows = []
    rows.append({
        "batch_id": result.batch_id,
        "source_file": result.source_file,
        "created": result.created_count,
        "updated": result.updated_count,
        "skipped": result.skipped_count,
        "errors": result.error_count,
        "applied": result.applied_count,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rows": [asdict(row) for row in result.rows],
    })
    save_json(log_path, rows[-100:])


def apply_import_preview(
    preview: ImportPreview,
    *,
    existing_inventory: Mapping[str, Mapping[str, Any]] | None,
    save_inventory_fn: Callable[[dict], Any],
    create_catalog_product_fn: Callable[[dict], Any] = create_product_with_variants_v5,
    refresh_catalog_fn: Callable[[], Any] = refresh_product_catalog_cache,
    write_batch_log_fn: Callable[[ImportApplyResult], Any] | None = None,
    source_file: str = "",
    imported_on: str | None = None,
) -> ImportApplyResult:
    """Apply valid preview rows and leave invalid/skipped rows untouched."""
    batch_id = uuid4().hex
    today = imported_on or today_str()
    inventory = {
        str(name): dict(item or {})
        for name, item in dict(existing_inventory or {}).items()
    }
    results: list[ImportApplyRowResult] = []
    catalog_payloads: list[tuple[int, str, dict]] = []
    changed = False

    if preview.errors:
        for issue in preview.errors:
            results.append(ImportApplyRowResult(
                row_number=issue.row_number,
                action="error",
                item_name="",
                status="error",
                message=issue.message,
            ))

    for row in preview.rows:
        item_name = _target_inventory_name(row)
        if row.action == "error" or row.errors:
            results.append(ImportApplyRowResult(
                row_number=row.row_number,
                action="error",
                item_name=item_name,
                status="error",
                message=_row_error(row),
            ))
            continue
        if row.action == "skip":
            results.append(ImportApplyRowResult(
                row_number=row.row_number,
                action="skip",
                item_name=item_name,
                status="skipped",
                message="Existing item skipped",
            ))
            continue
        if row.action not in {"create", "update"}:
            results.append(ImportApplyRowResult(
                row_number=row.row_number,
                action=row.action,
                item_name=item_name,
                status="error",
                message=f"Unsupported import action: {row.action}",
            ))
            continue
        if not item_name or not row.inventory_item:
            results.append(ImportApplyRowResult(
                row_number=row.row_number,
                action=row.action,
                item_name=item_name,
                status="error",
                message="Validated inventory payload is missing",
            ))
            continue

        matched_name = _matched_inventory_name(row)
        old_name = matched_name if row.action == "update" and matched_name in inventory else item_name
        duplicate_target = item_name in inventory and item_name != old_name
        if duplicate_target:
            results.append(ImportApplyRowResult(
                row_number=row.row_number,
                action=row.action,
                item_name=item_name,
                status="error",
                message=f"Target item already exists: {item_name}",
            ))
            continue

        if old_name != item_name:
            inventory.pop(old_name, None)
        inventory[item_name] = _inventory_payload(row.inventory_item, today)
        catalog_payloads.append((row.row_number, item_name, row.catalog_payload))
        results.append(ImportApplyRowResult(
            row_number=row.row_number,
            action=row.action,
            item_name=item_name,
            status="applied",
        ))
        changed = True

    if changed:
        try:
            save_inventory_fn(inventory)
        except Exception as exc:
            message = f"Inventory save failed: {exc}"
            app_log(f"[product import apply] {message}")
            results = [
                ImportApplyRowResult(
                    row_number=row.row_number,
                    action=row.action,
                    item_name=row.item_name,
                    status="error" if row.status == "applied" else row.status,
                    message=message if row.status == "applied" else row.message,
                )
                for row in results
            ]
            changed = False

    if changed:
        for row_number, item_name, catalog_payload in catalog_payloads:
            try:
                create_catalog_product_fn(catalog_payload)
            except Exception as exc:
                message = f"Inventory saved, but catalog sync failed: {exc}"
                app_log(f"[product import apply] {item_name}: {message}")
                results = [
                    ImportApplyRowResult(r.row_number, r.action, r.item_name, "error", message)
                    if r.row_number == row_number and r.status == "applied"
                    else r
                    for r in results
                ]
        try:
            refresh_catalog_fn()
        except Exception as exc:
            app_log(f"[product import apply refresh] {exc}")

    result = ImportApplyResult(
        batch_id=batch_id,
        source_file=source_file,
        rows=tuple(results),
    )
    if write_batch_log_fn is None:
        _append_batch_log(result)
    else:
        write_batch_log_fn(result)
    return result
