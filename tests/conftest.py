"""Test configuration — make plugin modules importable standalone."""
import sys
from pathlib import Path

# Add plugin root to path so `import engine` and `import tools` work
_plugin_root = str(Path(__file__).parent.parent)
if _plugin_root not in sys.path:
    sys.path.insert(0, _plugin_root)
