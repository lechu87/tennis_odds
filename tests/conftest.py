import os
import sys

# Scrapers live at repo root as flat modules (not a package), so make them importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
