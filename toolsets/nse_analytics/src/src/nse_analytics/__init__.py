"""NSE market desk analytics tools for SAM STR (toolset).

Pure calculations live in ``parsing``, ``universe``, ``rotation`` and ``live``
(unit-tested without SAM). Console-script entry points live in ``tools``;
each is a ``tool_cli(...)`` callable referenced from pyproject.toml's
[project.scripts].
"""

__all__ = ["live", "parsing", "rotation", "tools", "universe"]
