from __future__ import annotations

import json
import pickle

import google_backup


class FakeCredentials:
    def __init__(self, token="fresh"):
        self.token = token
        self.valid = True
        self.expired = False
        self.refresh_token = ""

    def to_json(self):
        return json.dumps({"token": self.token})

    @classmethod
    def from_authorized_user_file(cls, path, scopes):
        data = json.loads(open(path, "r", encoding="utf-8").read())
        return cls(data["token"])


def test_google_credentials_are_saved_as_json(monkeypatch, tmp_path):
    token_json = tmp_path / "gdrive_token.json"
    monkeypatch.setattr(google_backup, "GDRIVE_TOKEN_JSON", str(token_json))

    google_backup._save_google_credentials(FakeCredentials("json-token"))

    assert token_json.exists()
    assert json.loads(token_json.read_text(encoding="utf-8"))["token"] == "json-token"


def test_google_pickle_token_migrates_to_json_and_renames_legacy(monkeypatch, tmp_path):
    token_json = tmp_path / "gdrive_token.json"
    token_pickle = tmp_path / "gdrive_token.pickle"
    with open(token_pickle, "wb") as f:
        pickle.dump(FakeCredentials("legacy-token"), f)

    monkeypatch.setattr(google_backup, "GDRIVE_TOKEN_JSON", str(token_json))
    monkeypatch.setattr(google_backup, "LEGACY_GDRIVE_TOKEN_PICKLE", str(token_pickle))

    creds = google_backup._load_google_credentials(FakeCredentials)

    assert creds.token == "legacy-token"
    assert token_json.exists()
    assert not token_pickle.exists()
    assert token_pickle.with_suffix(".pickle.migrated").exists()
