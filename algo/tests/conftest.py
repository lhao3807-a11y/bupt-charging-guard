"""algo/tests 共享 fixture：把仓库根目录加入 sys.path，保证 ``import algo.*`` 可用。"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
