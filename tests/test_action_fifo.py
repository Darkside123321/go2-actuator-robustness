import unittest
import torch
from go2_robust.actions import ActionFIFO

class DelayContract(unittest.TestCase):
    def test_zero_lag_is_identity(self):
        f=ActionFIFO(2,3,0,0)
        a=torch.arange(6.).reshape(2,3)
        torch.testing.assert_close(f.push(a),a)

    def test_two_ticks_hold_neutral_then_release(self):
        f=ActionFIFO(1,1,2,2)
        values=[f.push(torch.tensor([[float(x)]])).item() for x in [1,2,3,4]]
        self.assertEqual(values,[0,0,1,2])

    def test_reset_only_selected_episode(self):
        f=ActionFIFO(2,1,1,1)
        f.push(torch.tensor([[1.],[10.]]))
        f.reset(torch.tensor([0]))
        torch.testing.assert_close(f.push(torch.tensor([[2.],[20.]])),
                                   torch.tensor([[0.],[10.]]))
        torch.testing.assert_close(f.push(torch.tensor([[3.],[30.]])),
                                   torch.tensor([[2.],[20.]]))

    def test_invalid_lag_is_rejected(self):
        with self.assertRaises(ValueError): ActionFIFO(1,1,2,1)

if __name__ == "__main__": unittest.main()
