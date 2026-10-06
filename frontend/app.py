"""
MarketLens — Frontend Entry Point

Runs the main dashboard by exec-ing dashboard.py.
Streamlit requires direct script execution, not module imports.
"""

import os
import sys
import runpy

# Ensure root directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
os.chdir(root_dir)

# Execute dashboard.py as a script (not import)
dashboard_path = os.path.join(root_dir, "dashboard.py")
exec(open(dashboard_path, encoding="utf-8").read())
