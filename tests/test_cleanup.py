import tempfile
import unittest
from pathlib import Path
import numpy as np
from plyfile import PlyData, PlyElement
from splat_cleanup import cleanup


class CleanupTest(unittest.TestCase):
    def test_preserves_attributes_and_source(self):
        dtype = [(n, "f4") for n in ("x","y","z","opacity","scale_0","scale_1","scale_2","rot_0","f_dc_0")]
        data = np.zeros(3, dtype=dtype)
        data["x"] = [0, 1, 20]
        data["opacity"] = [5, -5, 5]
        data["scale_0"] = [0, 0, 4]
        with tempfile.TemporaryDirectory() as d:
            source, dest = Path(d)/"source.ply", Path(d)/"filtered.ply"
            PlyData([PlyElement.describe(data, "vertex")], text=False).write(source)
            result = cleanup(source, dest, min_opacity=0.1, max_axis=3)
            self.assertEqual(result["output"], 1)
            self.assertEqual(len(PlyData.read(source)["vertex"].data), 3)
            self.assertEqual(PlyData.read(dest)["vertex"].data.dtype.names, data.dtype.names)


if __name__ == "__main__":
    unittest.main()
