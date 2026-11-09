import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT = "1425b15f73bd4095f0df53709d7c389c3eb9e790"

def setup():
    path = Path(os.environ.get("UNITREE_RL_MJLAB", ROOT.parent / "unitree_rl_mjlab")).resolve()
    if not (path / "scripts/train.py").is_file():
        raise FileNotFoundError("Set UNITREE_RL_MJLAB to the existing official checkout")
    sys.path.insert(0, str(path))
    return path
