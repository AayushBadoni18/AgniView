"""Credential-free shipped-image check: real COG creation and windowed reading."""
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy
import rasterio
from rasterio.transform import from_origin

from .external import RasterioPointReader


def main():
    with TemporaryDirectory() as directory:
        paths = tuple(str(Path(directory) / f"{band}.tif") for band in ("nir", "swir2", "fmask"))
        for path, value in zip(paths, (8000, 2000, 0)):
            with rasterio.open(path, "w", driver="COG", height=3, width=3, count=1,
                               dtype="int16", crs="EPSG:4326", transform=from_origin(0, 3, 1, 1),
                               nodata=-9999) as dataset:
                dataset.write(numpy.full((3, 3), value, dtype="int16"), 1)
        result = RasterioPointReader().read_observation(paths, 1.5, 1.5)
        assert result["nir"] == .8 and result["swir"] == .2 and result["validPixels"] == 9
    print("Rasterio import and local COG read passed")


if __name__ == "__main__":
    main()
