"""Load pure integration modules without installing Home Assistant."""

import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[1]
CUSTOM_COMPONENTS = ROOT / "custom_components"
INTEGRATION = CUSTOM_COMPONENTS / "rss_parser"

custom_components = ModuleType("custom_components")
custom_components.__path__ = [str(CUSTOM_COMPONENTS)]
rss_parser = ModuleType("custom_components.rss_parser")
rss_parser.__path__ = [str(INTEGRATION)]
sys.modules.setdefault("custom_components", custom_components)
sys.modules.setdefault("custom_components.rss_parser", rss_parser)
