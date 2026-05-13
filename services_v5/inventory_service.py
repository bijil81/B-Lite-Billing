"""Workflow layer for inventory and stock movements."""

from __future__ import annotations

from db_core.connection import connection_scope
from repositories.inventory_repo import InventoryRepository
from services_v5.product_catalog_service import ProductCatalogService


class InventoryService:
    def __init__(
        self,
        repo: InventoryRepository | None = None,
        catalog_service: ProductCatalogService | None = None,
    ):
        self.repo = repo or InventoryRepository()
        self.catalog_service = catalog_service or ProductCatalogService()

    def list_items(self) -> list[dict]:
        return self.repo.list_items()

    def _active_service_names(self) -> set[str]:
        try:
            from services_v5.service_master_service import ServiceMasterService
            grouped = ServiceMasterService().list_grouped_services(active_only=True)
        except Exception:
            return set()
        names: set[str] = set()
        for items in grouped.values():
            for name in items.keys():
                text = str(name or "").strip().lower()
                if text:
                    names.add(text)
        return names

    def purge_service_named_items(self) -> list[str]:
        """Deactivate inventory rows that are actually service-master entries."""
        service_names = self._active_service_names()
        if not service_names:
            return []
        removed: list[str] = []
        for item in self.repo.list_items():
            name = str(item.get("legacy_name", "") or "").strip()
            if not name or name.lower() not in service_names:
                continue
            if not bool(item.get("active", 1)):
                continue
            self.repo.deactivate_item(name)
            try:
                self.catalog_service.deactivate_variants_for_inventory_name(name)
            except Exception:
                pass
            removed.append(name)
        return removed

    def build_legacy_inventory_map(self, active_only: bool = True) -> dict:
        result = {}
        service_names = self._active_service_names()
        for item in self.repo.list_items():
            if active_only and not bool(item.get("active", 1)):
                continue
            # Soft-delete: skip deleted items in the default active catalog view.
            if active_only and bool(item.get("is_deleted", 0)):
                continue
            name = item.get("legacy_name", "")
            if str(name or "").strip().lower() in service_names:
                continue
            min_qty = float(item.get("min_qty", 0.0) or 0.0)
            result[name] = {
                "category": item.get("category", ""),
                "brand": item.get("brand", ""),
                "unit": item.get("unit", "pcs"),
                "qty": float(item.get("current_qty", 0.0) or 0.0),
                "min_qty": min_qty,
                "min_stock": min_qty if min_qty > 0 else 5.0,
                "cost": float(item.get("cost_price", 0.0) or 0.0),
                "price": float(item.get("sale_price", 0.0) or 0.0),
                "inactive": not bool(item.get("active", 1)),
                "is_deleted": bool(item.get("is_deleted", 0)),
            }
        try:
            for variant in self.catalog_service.build_inventory_rows():
                name = (
                    str(variant.get("bill_label", "")).strip()
                    or str(variant.get("display_name", "")).strip()
                    or str(variant.get("variant_name", "")).strip()
                )
                if not name or name not in result:
                    continue
                result[name].update({
                    "barcode": variant.get("barcode", ""),
                    "sku": variant.get("sku", ""),
                    "bill_label": variant.get("bill_label", name),
                    "base_product": variant.get("product_base_name", variant.get("product_name", name)),
                    "pack_size": variant.get("unit_value", ""),
                    "sale_unit": variant.get("sale_unit", variant.get("unit_type", "pcs")),
                    "base_unit": variant.get("base_unit", variant.get("unit_type", "pcs")),
                    "unit_multiplier": variant.get("unit_multiplier", 1.0),
                    "allow_decimal_qty": bool(variant.get("allow_decimal_qty", 0)),
                    "is_weighed": bool(variant.get("is_weighed", 0)),
                    "mrp": float(variant.get("mrp", 0.0) or 0.0),
                    "gst_rate": float(variant.get("gst_rate", 0.0) or 0.0),
                    "cess_rate": float(variant.get("cess_rate", 0.0) or 0.0),
                    "hsn_sac": variant.get("hsn_sac", ""),
                    "price_includes_tax": bool(variant.get("price_includes_tax", 1)),
                })
        except Exception as e:
            try:
                from utils import app_log
                app_log(f"[InventoryService.build_legacy_inventory_map] Variant catalog merge failed: {e}")
            except Exception:
                print(f"[InventoryService.build_legacy_inventory_map] Variant catalog merge failed: {e}")
        return result


    def sync_legacy_inventory_map(self, data: dict) -> None:
        incoming_keys = set()
        service_names = self._active_service_names()
        for key, item in data.items():
            if str(key or "").strip().lower() in service_names:
                continue
            incoming_keys.add(key)
            row = {
                "legacy_name": key,
                "category": item.get("category", ""),
                "brand": item.get("brand", ""),
                "unit": item.get("unit", "pcs"),
                "current_qty": item.get("qty", item.get("quantity", item.get("stock", 0.0))),
                "min_qty": item.get("min_qty", item.get("min_stock", 0.0)),
                "cost_price": item.get("cost", item.get("cost_price", 0.0)),
                "sale_price": item.get("price", item.get("sale_price", item.get("cost", item.get("cost_price", 0.0)))),
                "active": not bool(item.get("inactive", False)),
            }
            self.repo.upsert_item(row)
            self.catalog_service.sync_inventory_row({
                **row,
                "bill_label": item.get("bill_label", key),
                "base_product": item.get("base_product", key),
                "pack_size": item.get("pack_size", ""),
                "barcode": item.get("barcode", ""),
                "sku": item.get("sku", ""),
                "sale_unit": item.get("sale_unit", item.get("unit", "pcs")),
                "base_unit": item.get("base_unit", item.get("unit", "pcs")),
                "unit_multiplier": item.get("unit_multiplier", 1.0),
                "allow_decimal_qty": item.get("allow_decimal_qty", False),
                "is_weighed": item.get("is_weighed", False),
                "mrp": item.get("mrp", 0.0),
                "gst_rate": item.get("gst_rate", 0.0),
                "cess_rate": item.get("cess_rate", 0.0),
                "hsn_sac": item.get("hsn_sac", ""),
                "price_includes_tax": item.get("price_includes_tax", True),
            })

        for existing in self.repo.list_items():
            legacy_name = existing.get("legacy_name", "")
            if legacy_name and legacy_name not in incoming_keys and bool(existing.get("active", 1)):
                self.repo.deactivate_item(legacy_name)
                self.catalog_service.deactivate_variants_for_inventory_name(legacy_name)

    def update_quantity(self, legacy_name: str, current_qty: float) -> None:
        """Fast one-item stock update used by the Inventory quick update UI."""

        existing = self.repo.get_item(legacy_name)
        if not existing:
            raise ValueError(f"Inventory item not found: {legacy_name}")
            
        old_qty = float(existing.get("current_qty", 0.0) or 0.0)
        qty_delta = current_qty - old_qty
            
        self.repo.update_quantity(legacy_name, current_qty)
        existing["current_qty"] = float(current_qty or 0.0)
        self.catalog_service.sync_inventory_row(existing)
        
        if qty_delta != 0:
            movement_type = "purchase" if qty_delta > 0 else "adjustment"
            self.repo.add_movement({
                "legacy_name": legacy_name,
                "movement_type": movement_type,
                "qty_delta": qty_delta,
                "reference_type": "quick_update",
                "reference_id": "",
                "note": "Quick stock update",
            })

    # ------------------------------------------------------------------
    # Stock Reduction (Phase 2) — Damage / Wastage / Expiry
    # ------------------------------------------------------------------

    VALID_REDUCTION_REASONS = (
        "Damaged",
        "Expired",
        "Wastage",
        "Theft",
        "Quality Rejection",
        "Other",
    )

    def reduce_stock(
        self,
        legacy_name: str,
        qty: float,
        reason: str,
        reduced_by: str = "",
    ) -> None:
        """Reduce stock for non-sale reasons (damage, wastage, expiry, etc.).

        Args:
            legacy_name: Exact item name as stored in the inventory.
            qty:         Quantity to deduct. Must be > 0.
            reason:      Non-empty reason string.  Should be one of
                         VALID_REDUCTION_REASONS but any non-empty string
                         is accepted to allow custom free-text reasons.
            reduced_by:  Username performing the reduction (for audit log).

        Raises:
            ValueError: with a user-readable message if:
                - qty <= 0
                - reason is empty
                - item does not exist
                - qty exceeds available stock
        """
        # --- Input validation ---
        if qty is None or qty <= 0:
            raise ValueError(
                f"Reduction quantity must be greater than 0. Got: {qty}"
            )

        reason = str(reason or "").strip()
        if not reason:
            raise ValueError("A reason is required for stock reduction.")

        legacy_name = str(legacy_name or "").strip()
        if not legacy_name:
            raise ValueError("Item name cannot be empty.")

        # --- Stock availability check (read-before-write inside same connection) ---
        existing = self.repo.get_item(legacy_name)
        if not existing:
            raise ValueError(
                f"Inventory item '{legacy_name}' not found. "
                "Check the item name and try again."
            )

        available_qty = float(existing.get("current_qty", 0.0) or 0.0)

        if qty > available_qty:
            raise ValueError(
                f"Cannot reduce {qty} units of '{legacy_name}': "
                f"only {available_qty} units are in stock."
            )

        new_qty = round(available_qty - qty, 6)

        # --- Persist quantity change ---
        self.repo.update_quantity(legacy_name, new_qty)
        existing["current_qty"] = new_qty
        self.catalog_service.sync_inventory_row(existing)

        # --- Movement log (Phase 4 ready) ---
        note = f"Reason: {reason}"
        if reduced_by:
            note += f" | By: {reduced_by}"

        self.repo.add_movement({
            "legacy_name": legacy_name,
            "movement_type": "damage",
            "qty_delta": -qty,
            "reference_type": "manual_reduction",
            "reference_id": "",
            "note": note,
        })

    def save_item(self, payload: dict) -> None:
        self.repo.upsert_item(payload)
        self.catalog_service.sync_inventory_row(payload)

    def delete_item(self, legacy_name: str) -> None:
        """Soft-delete: sets active=0 and is_deleted=1 with audit."""
        try:
            from soft_delete import soft_delete_product
            soft_delete_product(legacy_name, deleted_by="")
        except Exception as e:
            try:
                from utils import app_log
                app_log(f"[InventoryService.delete_item] soft_delete_product failed for '{legacy_name}': {e}")
            except Exception:
                print(f"[InventoryService.delete_item] soft_delete_product failed for '{legacy_name}': {e}")
        self.repo.deactivate_item(legacy_name)

        self.catalog_service.deactivate_variants_for_inventory_name(legacy_name)

    def restore_item(self, legacy_name: str) -> None:
        try:
            from soft_delete import restore_product
            restore_product(legacy_name, restored_by="")
        except Exception as e:
            try:
                from utils import app_log
                app_log(f"[InventoryService.restore_item] restore_product failed for '{legacy_name}': {e}")
            except Exception:
                print(f"[InventoryService.restore_item] restore_product failed for '{legacy_name}': {e}")

        with connection_scope() as conn:
            conn.execute(
                "UPDATE v5_inventory_items SET active = 1, is_deleted = 0, deleted_at = '', deleted_by = '', updated_at = datetime('now') WHERE legacy_name = ?",
                (legacy_name,),
            )
            row = conn.execute(
                "SELECT * FROM v5_inventory_items WHERE legacy_name = ?",
                (legacy_name,),
            ).fetchone()
            conn.commit()
        if row:
            self.catalog_service.sync_inventory_row({
                "legacy_name": row["legacy_name"],
                "category": row["category"],
                "brand": row["brand"],
                "unit": row["unit"],
                "current_qty": row["current_qty"],
                "min_qty": row["min_qty"],
                "cost_price": row["cost_price"],
                "sale_price": row["sale_price"],
                "active": True,
            })

    def permanent_delete_item(self, legacy_name: str, deleted_by: str = "") -> bool:
        try:
            from soft_delete import permanent_delete_product
            return permanent_delete_product(legacy_name, deleted_by)
        except Exception:
            return False

    def record_movement(self, payload: dict) -> None:
        self.repo.add_movement(payload)
