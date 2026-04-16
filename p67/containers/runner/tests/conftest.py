"""
Make host_gs importable from this tests/ subdirectory.
"""

from __future__ import annotations

import os
import sys

# Add containers/runner/ to sys.path so `import host_gs` resolves.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
