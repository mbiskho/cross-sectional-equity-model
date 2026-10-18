import unittest

from cross_sectional.engine import analyze, load_rows


class CrossSectionalTests(unittest.TestCase):
    def test_sample_quantile_returns_and_rank_ic(self):
        result = analyze(load_rows("data/cross_sectional.csv"), quantiles=3)
        self.assertEqual(result["dates"], 4)
        self.assertEqual(result["quantiles"], 3)
        means = result["mean_forward_return_by_quantile"]
        self.assertEqual(len(means), 3)
        self.assertGreater(means[-1], means[0])
        self.assertGreater(result["mean_rank_ic"], 0)
        self.assertIn("rank_ic_information_ratio", result)
        self.assertIn("mean_top_minus_bottom_return", result)
        self.assertIn("positive_date_fraction", result["quantile_summary"]["1"])

    def test_rejects_duplicate_rows(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load_rows("tests/duplicate.csv")

    def test_single_bucket_can_have_no_ic(self):
        rows = [
            {"date": "d", "security": "A", "value": 1.0, "momentum": 1.0, "quality": 1.0, "forward_return": 0.0},
            {"date": "d", "security": "B", "value": 1.0, "momentum": 1.0, "quality": 1.0, "forward_return": 0.1},
        ]
        result = analyze(rows, quantiles=2)
        self.assertIsNone(result["mean_rank_ic"])


if __name__ == "__main__":
    unittest.main()
