"""Write the current OpenAPI document to contract/openapi.json."""

import json
from pathlib import Path

from ticket_api.main import app

path = Path("contract/openapi.json")
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
print(f"Wrote {path}")
