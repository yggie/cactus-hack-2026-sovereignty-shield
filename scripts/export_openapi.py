"""Export the FastAPI OpenAPI spec to frontend/openapi.json."""

import json
import sys
from pathlib import Path

# Add project root to path so we can import api
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from api import app

spec = app.openapi()
out = root / "frontend" / "openapi.json"
out.write_text(json.dumps(spec, indent=2))
print(f"Wrote OpenAPI spec to {out}")
