"""Workflow layer for relational service master storage."""

from __future__ import annotations

from repositories.services_repo import ServicesRepository


class ServiceMasterService:
    def __init__(self, repo: ServicesRepository | None = None):
        self.repo = repo or ServicesRepository()

    def has_services(self) -> bool:
        return bool(self.repo.list_services(active_only=False))

    def list_grouped_services(self, *, active_only: bool = True) -> dict[str, dict[str, float]]:
        grouped: dict[str, dict[str, float]] = {}
        for row in self.repo.list_services(active_only=active_only):
            legacy_name = str(row.get("legacy_name", "")).strip()
            if not legacy_name:
                continue
            category = str(row.get("category", "")).strip() or "General"
            grouped.setdefault(category, {})[legacy_name] = float(row.get("price", 0.0) or 0.0)
        return grouped

    def sync_grouped_services(self, data: dict, *, deactivate_missing: bool = False) -> None:
        keep_names: list[str] = []
        for category, items in self._normalize_grouped_services(data).items():
            for name, price in items.items():
                keep_names.append(name)
                self.repo.upsert_service({
                    "legacy_name": name,
                    "category": category,
                    "price": price,
                    "active": True,
                })
        if deactivate_missing:
            self.repo.deactivate_missing(keep_names)

    def import_legacy_payload(self, payload: dict, *, deactivate_missing: bool = False) -> None:
        if not isinstance(payload, dict):
            return
        if "Services" in payload or "Products" in payload:
            self.sync_grouped_services(payload.get("Services", {}), deactivate_missing=deactivate_missing)
            return
        self.sync_grouped_services(payload, deactivate_missing=deactivate_missing)

    @staticmethod
    def _normalize_grouped_services(data: dict) -> dict[str, dict[str, float]]:
        grouped: dict[str, dict[str, float]] = {}
        if not isinstance(data, dict):
            return grouped
        for category, items in data.items():
            category_name = str(category or "").strip() or "General"
            if not isinstance(items, dict):
                continue
            bucket = grouped.setdefault(category_name, {})
            for name, price in items.items():
                legacy_name = str(name or "").strip()
                if not legacy_name:
                    continue
                try:
                    bucket[legacy_name] = float(price or 0.0)
                except Exception:
                    bucket[legacy_name] = 0.0
        return grouped
