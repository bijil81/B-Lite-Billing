from services_v5.inventory_service import InventoryService


class FakeInventoryRepo:
    def __init__(self):
        self.rows = []
        self.upserts = []
        self.deactivated = []

    def list_items(self):
        return list(self.rows)

    def upsert_item(self, payload):
        self.upserts.append(payload)

    def deactivate_item(self, legacy_name):
        self.deactivated.append(legacy_name)


class FakeCatalogService:
    def __init__(self):
        self.deactivated = []
        self.synced = []

    def build_inventory_rows(self):
        return []

    def sync_inventory_row(self, payload):
        self.synced.append(payload)

    def deactivate_variants_for_inventory_name(self, legacy_name):
        self.deactivated.append(legacy_name)


def test_inventory_map_excludes_active_service_names(monkeypatch):
    repo = FakeInventoryRepo()
    repo.rows = [
        {"legacy_name": "Hair Cut", "category": "Hair", "active": 1, "is_deleted": 0},
        {"legacy_name": "Shampoo Bottle", "category": "Retail", "active": 1, "is_deleted": 0},
    ]
    service = InventoryService(repo=repo, catalog_service=FakeCatalogService())
    monkeypatch.setattr(service, "_active_service_names", lambda: {"hair cut"})

    result = service.build_legacy_inventory_map()

    assert "Hair Cut" not in result
    assert "Shampoo Bottle" in result


def test_inventory_sync_skips_active_service_names(monkeypatch):
    repo = FakeInventoryRepo()
    service = InventoryService(repo=repo, catalog_service=FakeCatalogService())
    monkeypatch.setattr(service, "_active_service_names", lambda: {"hair cut"})

    service.sync_legacy_inventory_map({
        "Hair Cut": {"category": "Hair", "price": 100},
        "Shampoo Bottle": {"category": "Retail", "price": 200},
    })

    assert [row["legacy_name"] for row in repo.upserts] == ["Shampoo Bottle"]


def test_purge_service_named_items_deactivates_contaminated_rows(monkeypatch):
    repo = FakeInventoryRepo()
    repo.rows = [
        {"legacy_name": "Hair Cut", "active": 1},
        {"legacy_name": "Shampoo Bottle", "active": 1},
    ]
    catalog = FakeCatalogService()
    service = InventoryService(repo=repo, catalog_service=catalog)
    monkeypatch.setattr(service, "_active_service_names", lambda: {"hair cut"})

    removed = service.purge_service_named_items()

    assert removed == ["Hair Cut"]
    assert repo.deactivated == ["Hair Cut"]
    assert catalog.deactivated == ["Hair Cut"]
