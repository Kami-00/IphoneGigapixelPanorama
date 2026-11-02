import tempfile,unittest
from pathlib import Path
import numpy as np
from stack import combine,process
class StackTests(unittest.TestCase):
    def test_mean_and_median_across_stripes(self):
        with tempfile.TemporaryDirectory() as d:
            arrays=[np.full((129,17,3),v,np.uint8) for v in [0,30,255]]
            mean,median=combine(arrays,Path(d))
            self.assertTrue(np.all(mean==95));self.assertTrue(np.all(median==30))
    def test_single_image_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'result'
            with self.assertRaises(ValueError):process([Path('missing.jpg')],output)
            self.assertFalse(output.exists())
if __name__=='__main__':unittest.main()
