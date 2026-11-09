"""Use the upstream interactive viewer with the extension observation layout."""
import runpy
import sys
from .upstream import setup
from .tasks import register
if __name__=="__main__":
    upstream=setup();register()
    runpy.run_path(str(upstream/"scripts/play.py"),run_name="__main__")
