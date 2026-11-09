import unittest
from go2_robust.evaluate import command_at, optional_rmse
class MetricContract(unittest.TestCase):
    def test_rmse_uses_squared_sum(self):
        self.assertEqual(optional_rmse(25,4),2.5)
    def test_no_valid_sample_has_no_score(self):
        self.assertIsNone(optional_rmse(0,0))
    def test_command_boundary(self):
        profile=[{"start_s":0,"velocity":[0,0,0]},
                 {"start_s":2,"velocity":[0.5,0,0]}]
        self.assertEqual(command_at(profile,1.98),[0,0,0])
        self.assertEqual(command_at(profile,2),[0.5,0,0])
if __name__=="__main__":unittest.main()
