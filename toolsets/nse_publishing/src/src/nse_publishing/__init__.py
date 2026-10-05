"""NSE market desk publishing tool for SAM STR (toolset).

``render`` converts a markdown note to print-ready HTML with charts inlined
(unit-tested without SAM); ``tools`` holds the ``tool_cli`` entry point
referenced from pyproject.toml's [project.scripts].
"""

__all__ = ["render", "tools"]
