import sys
from pathlib import Path

# The app package lives under src/app (that is what ships to the Databricks App),
# so the shared calculation module is importable as `server.optimisation_demo.core`.
APP = Path(__file__).resolve().parents[2] / "src" / "app"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
