import copy
import unittest
from statistics import mean

from _helpers import BREADTH_FILES, compare_payloads, fixture_payload

from nse_analytics import live, rotation, universe


class UniverseTest(unittest.TestCase):
    def test_fifty_unique_symbols(self):
        rows = universe.load_universe()
        self.assertEqual(len(rows), 50)
        self.assertEqual(len({r["symbol"] for r in rows}), 50)
        self.assertTrue(all(r["desk_sector"] for r in rows))

    def test_batches_respect_compare_limit_and_cover_all(self):
        rows = universe.load_universe()
        batches = universe.compare_batches(rows)
        self.assertTrue(all(1 <= len(b) <= 10 for b in batches))
        self.assertEqual(sorted(s for b in batches for s in b), sorted(r["symbol"] for r in rows))

    def test_banks_split_from_financials(self):
        secs = universe.sectors(universe.load_universe())
        self.assertIn("HDFCBANK", secs["Banks"])
        self.assertIn("BAJFINANCE", secs["Financials ex-Banks"])


class SectorRotationTest(unittest.TestCase):
    def setUp(self):
        self.rows = universe.load_universe()
        self.result = rotation.sector_rotation(self.rows, compare_payloads(1), compare_payloads(3))

    def test_full_coverage(self):
        cov = self.result["coverage"]
        self.assertEqual(cov["missing"], [])
        self.assertEqual(cov["included"] + len(cov["flagged"]), 50)

    def test_benchmark_is_equal_weight_mean(self):
        flagged = set(self.result["coverage"]["flagged"])
        s1 = {s["symbol"]: s["return_pct"] for p in compare_payloads(1) for s in p["stocks"]}
        expected = mean(v for k, v in s1.items() if k not in flagged)
        self.assertAlmostEqual(self.result["benchmark"]["ret_1m"], round(expected, 2), places=2)

    def test_quadrants_match_rs_signs(self):
        for s in self.result["sectors"]:
            expected = rotation._quadrant(s["rs_3m"], s["rs_1m"])
            self.assertEqual(s["quadrant"], expected, s)
        listed = sum(len(v) for v in self.result["quadrants"].values())
        self.assertEqual(listed, len(self.result["sectors"]))

    def test_sectors_sorted_by_rs_3m(self):
        rs = [s["rs_3m"] for s in self.result["sectors"]]
        self.assertEqual(rs, sorted(rs, reverse=True))

    def test_csv_outputs(self):
        csvs = self.result["csv"]
        self.assertTrue(csvs["sector_rotation.csv"].startswith("sector,constituents,included,"))
        self.assertEqual(csvs["momentum_ranking.csv"].count("\n"), 51)  # header + 50 stocks

    def test_outlier_is_flagged_and_excluded(self):
        three = copy.deepcopy(compare_payloads(3))
        three[0]["stocks"][0]["return_pct"] = -52.0  # e.g. a 1:1 bonus inside the window
        sym = three[0]["stocks"][0]["symbol"]
        result = rotation.sector_rotation(self.rows, compare_payloads(1), three)
        self.assertIn(sym, result["coverage"]["flagged"])
        self.assertNotIn(sym, [s["symbol"] for s in result["bottom_momentum"]])

    def test_missing_symbols_reported(self):
        one = compare_payloads(1)[1:]  # drop the first batch
        result = rotation.sector_rotation(self.rows, one, compare_payloads(3))
        self.assertEqual(len(result["coverage"]["missing"]), 10)


class BreadthTrendTest(unittest.TestCase):
    def setUp(self):
        self.result = rotation.breadth_trend([fixture_payload(f) for f in BREADTH_FILES])

    def test_dedupes_today_and_holiday(self):
        self.assertEqual(self.result["sessions"], 5)
        self.assertEqual([d["date"] for d in self.result["days"]],
                         ["2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01"])

    def test_latest_regime_and_direction(self):
        latest = self.result["latest"]
        self.assertEqual(latest["date"], "2026-10-01")
        self.assertEqual(latest["regime"], "broad weakness")
        self.assertEqual(self.result["direction"], "deteriorating")

    def test_single_session(self):
        result = rotation.breadth_trend([fixture_payload("breadth_today.json")])
        self.assertEqual(result["sessions"], 1)
        self.assertTrue(result["direction"].startswith("n/a"))

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            rotation.breadth_trend([])


class LiveSectorTiltTest(unittest.TestCase):
    def setUp(self):
        self.rows = universe.load_universe()
        self.result = live.live_sector_tilt(
            self.rows, fixture_payload("live_gainers.json"), fixture_payload("live_losers.json"))

    def test_coverage(self):
        cov = self.result["coverage"]
        self.assertEqual(cov["seen"], 40)
        self.assertEqual(len(cov["unseen"]), 10)

    def test_sector_counts_add_up(self):
        self.assertEqual(sum(s["seen"] for s in self.result["sectors"]), 40)
        for s in self.result["sectors"]:
            self.assertLessEqual(s["up"] + s["down"], s["seen"])

    def test_sorted_and_timestamped(self):
        avgs = [s["avg_change_pct"] for s in self.result["sectors"]]
        self.assertEqual(avgs, sorted(avgs, reverse=True))
        self.assertIn("Oct-2026", self.result["as_of"])

    def test_no_rows_raises(self):
        with self.assertRaises(ValueError):
            live.live_sector_tilt(self.rows, {"data": {}}, {"data": {}})


if __name__ == "__main__":
    unittest.main()
