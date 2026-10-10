"""Write the current OpenAPI document to contract/openapi.json."""

import json
from pathlib import Path

from ticket_api.main import create_app

path = Path("contract/openapi.json")
path.parent.mkdir(exist_ok=True)
document = create_app().openapi()
path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {path}")
