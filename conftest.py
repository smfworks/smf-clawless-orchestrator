# pytest configuration: make the package importable from the repo root.
import os
import sys

# Tests always use the offline mock LLM, regardless of any machine-level config.
os.environ.setdefault("CLAWMES_LLM", "mock")

sys.path.insert(0, os.path.dirname(__file__))
