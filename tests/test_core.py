import unittest

from agent_core import kpi_snapshot, load_orders, root_causes, simulate_scenario


class CoreAnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_orders()

    def test_demo_kpis(self):
        kpis = kpi_snapshot(self.rows)
        self.assertEqual(kpis["total_orders"], 150)
        self.assertEqual(kpis["delivered_orders"], 129)
        self.assertEqual(kpis["open_orders"], 21)
        self.assertEqual(kpis["on_time_delivery_pct"], 35.7)
        self.assertEqual(kpis["high_risk_open_orders"], 9)

    def test_confirmation_scenario(self):
        scenario = simulate_scenario(self.rows, confirmation_days_saved=1)
        self.assertEqual(scenario["baseline_projected_otd_pct"], 35.7)
        self.assertEqual(scenario["scenario_projected_otd_pct"], 45.0)
        self.assertEqual(scenario["otd_delta_pp"], 9.3)
        self.assertEqual(scenario["scenario_high_risk_open"], 6)

    def test_root_cause_order(self):
        causes = root_causes(self.rows)
        self.assertTrue(causes)
        self.assertEqual(causes[0]["driver"], "Supplier confirmation delay")
        self.assertEqual(causes[0]["share_pct"], 46.4)


if __name__ == "__main__":
    unittest.main()
