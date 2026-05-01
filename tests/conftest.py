from __future__ import annotations

import os
from pathlib import Path


os.environ["APPDATA"] = str(Path(__file__).resolve().parents[1] / ".pytest_appdata")
