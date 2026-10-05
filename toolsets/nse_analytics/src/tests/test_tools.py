"""Exercise the SAM tool wrappers end to end (skipped if the tool SDK is not importable)."""

import asyncio
import unittest

from _helpers import BREADTH_FILES, fixture_raw

try:
    from sam_tool_sdk import Artifact

    from nse_analytics import tools
except ImportError:  # pragma: no cover - SDK only ships with SAM Desktop
    tools = None


def _art(name: str) -> "Artifact":
    return Artifact(content=fixture_raw(name).encode(), filename=name, version=1, mime_type="application/json")


@unittest.skipIf(tools is None, "sam_tool_sdk not importable")
class ToolWrappersTest(unittest.TestCase):
    def run_tool(self, coro):
        return asyncio.run(coro)

    def test_universe(self):
        res = self.run_tool(tools.get_nifty50_universe())
        self.assertEqual(res.status, "success")
        self.assertEqual(len(res.data["compare_batches"]), 5)

    def test_sector_rotation(self):
        res = self.run_tool(tools.sector_rotation(
            [_art(f"compare_1m_batch{i}.json") for i in range(1, 6)],
            [_art(f"compare_3m_batch{i}.json") for i in range(1, 6)],
        ))
        self.assertEqual(res.status, "success", res.message)
        self.assertEqual({d.name for d in res.data_objects}, {"sector_rotation.csv", "momentum_ranking.csv"})
        self.assertNotIn("csv", res.data)

    def test_breadth_trend(self):
        res = self.run_tool(tools.breadth_trend([_art(f) for f in BREADTH_FILES]))
        self.assertEqual(res.status, "success", res.message)
        self.assertEqual(res.data_objects[0].name, "breadth_trend.csv")

    def test_live_sector_tilt(self):
        res = self.run_tool(tools.live_sector_tilt(_art("live_gainers.json"), _art("live_losers.json")))
        self.assertEqual(res.status, "success", res.message)
        self.assertEqual(res.data["coverage"]["seen"], 40)

    def test_every_tool_uses_portable_injection(self):
        # Without an annotated ctx/Artifact parameter the SDK passes the context
        # positionally ("legacy injection"), which broke get_nifty50_universe().
        from sam_tool_sdk.tool_runner import _detect_special_params

        for fn in (tools.get_nifty50_universe, tools.sector_rotation, tools.breadth_trend, tools.live_sector_tilt):
            ctx_param, _ = _detect_special_params(fn)
            self.assertEqual(ctx_param, "ctx", fn.__name__)

    def test_runner_path_universe(self):
        # Same call path the STR uses: resolve by module/function name, inject, call.
        from sam_tool_sdk.tool_runner import _call_handler, _prepare_function_call

        func, pos, kwargs = _prepare_function_call("nse_analytics.tools", "get_nifty50_universe", {}, None, {})
        res = _call_handler(func, *pos, **kwargs)
        self.assertEqual(res.status, "success")

    def test_bad_artifact_returns_error_result(self):
        bad = Artifact(content=b"not json", filename="bad.json", version=1, mime_type="text/plain")
        res = self.run_tool(tools.breadth_trend([bad]))
        self.assertEqual(res.status, "error")


if __name__ == "__main__":
    unittest.main()
