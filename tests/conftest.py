"""Registers this directory as the ``api`` package under test.

In this repo, ``api/`` already sits at the root with that exact name, and
``pythonpath = ["."]`` in ``pyproject.toml`` is enough on its own - this
conftest is a no-op here. It earns its keep once ``api/`` is checked out on
its own (e.g. as ``master-splinter-api``): the clone directory isn't named
``api``, but every internal import in it still says ``from api.xxx import
y``, so without this, nothing below would resolve.

"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if "api" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "api", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["api"] = module
    spec.loader.exec_module(module)
