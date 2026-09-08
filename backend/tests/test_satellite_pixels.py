import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from agniview.external import RasterioPointReader


def write_observation(tmp_path, nir, swir, mask=None, *, changed_band=None, **metadata):
    arrays = (np.asarray(nir, dtype="float32"), np.asarray(swir, dtype="float32"),
              np.zeros(np.shape(nir), dtype="uint8") if mask is None else np.asarray(mask, dtype="uint8"))
    paths = []
    for index, values in enumerate(arrays):
        options = {"driver": "COG", "count": 1, "dtype": values.dtype,
                   "height": values.shape[0], "width": values.shape[1],
                   "crs": "EPSG:4326", "transform": from_origin(0, 3, 1, 1),
                   "nodata": 255 if index == 2 else -9999}
        if index == changed_band:
            options.update(metadata)
        path = tmp_path / f"band-{index}.tif"
        with rasterio.open(path, "w", **options) as dataset:
            dataset.write(values, 1)
        paths.append(str(path))
    return tuple(paths)


def test_cloudy_neighbors_are_excluded_from_both_band_medians(tmp_path):
    nir = [[9000, 9000, 9000], [9000, 2000, 4000], [9000, 6000, 8000]]
    swir = [[1000, 1000, 1000], [1000, 8000, 6000], [1000, 4000, 2000]]
    mask = [[2, 2, 2], [2, 0, 0], [2, 0, 0]]
    paths = write_observation(tmp_path, nir, swir, mask)
    result = RasterioPointReader().read_observation(paths, 1.5, 1.5)
    assert {key: result[key] for key in ("nir", "swir", "validPixels", "totalPixels")} == {
        "nir": pytest.approx(.5), "swir": pytest.approx(.5), "validPixels": 4, "totalPixels": 9}
    assert result["requestedWindowPixels"] == 3


@pytest.mark.parametrize("flag", [2, 4, 8, 16, 255], ids=["cloud", "adjacent", "shadow", "snow", "fill"])
def test_each_unusable_fmask_value_rejects_pixels(tmp_path, flag):
    paths = write_observation(tmp_path, np.full((3, 3), 8000), np.full((3, 3), 2000),
                              np.full((3, 3), flag))
    assert RasterioPointReader().read_observation(paths, 1.5, 1.5) is None


@pytest.mark.parametrize("band", [0, 1], ids=["nir", "swir"])
@pytest.mark.parametrize("invalid", [-9999, -1, 10001, np.nan, np.inf, -np.inf])
def test_invalid_reflectance_excluded_from_both_bands(tmp_path, band, invalid):
    arrays = [np.array([[1000, 2000, 3000], [4000, 5000, 6000], [7000, 8000, 9000]], dtype="float32"),
              np.array([[9000, 8000, 7000], [6000, 5000, 4000], [3000, 2000, 1000]], dtype="float32")]
    arrays[band][0, 0] = invalid
    paths = write_observation(tmp_path, *arrays)
    result = RasterioPointReader().read_observation(paths, 1.5, 1.5)
    assert {key: result[key] for key in ("nir", "swir", "validPixels", "totalPixels")} == {
        "nir": pytest.approx(.55), "swir": pytest.approx(.45), "validPixels": 8, "totalPixels": 9}


def test_disjoint_valid_band_pixels_are_not_combined(tmp_path):
    nir = [[8000, -9999, -9999], [-9999, -9999, -9999], [-9999, -9999, -9999]]
    swir = [[-9999, 2000, -9999], [-9999, -9999, -9999], [-9999, -9999, -9999]]
    paths = write_observation(tmp_path, nir, swir)
    assert RasterioPointReader().read_observation(paths, 1.5, 1.5) is None


@pytest.mark.parametrize("band", [1, 2], ids=["swir", "fmask"])
@pytest.mark.parametrize("metadata", [{"crs": "EPSG:3857"},
                                       {"transform": from_origin(.1, 3, 1, 1)}], ids=["crs", "transform"])
def test_misaligned_band_grids_are_rejected(tmp_path, band, metadata):
    paths = write_observation(tmp_path, np.full((3, 3), 8000), np.full((3, 3), 2000),
                              changed_band=band, **metadata)
    with pytest.raises(ValueError):
        RasterioPointReader().read_observation(paths, 1.5, 1.5)


@pytest.mark.parametrize("band", [1, 2], ids=["swir", "fmask"])
def test_mismatched_band_shape_is_rejected(tmp_path, band):
    arrays = [np.full((3, 3), 8000), np.full((3, 3), 2000), np.zeros((3, 3))]
    arrays[band] = arrays[band][:2, :]
    paths = write_observation(tmp_path, *arrays)
    with pytest.raises(ValueError):
        RasterioPointReader().read_observation(paths, 1.5, 1.5)


def test_edge_window_counts_only_pixels_inside_raster(tmp_path):
    paths = write_observation(tmp_path, [[1000, 3000, 9000], [5000, 7000, 9000], [9000, 9000, 9000]],
                              np.full((3, 3), 2000))
    result = RasterioPointReader().read_observation(paths, .5, 2.5)
    assert {key: result[key] for key in ("nir", "swir", "validPixels", "totalPixels")} == {
        "nir": pytest.approx(.4), "swir": pytest.approx(.2), "validPixels": 4, "totalPixels": 4}
    assert result["requestedWindowPixels"] == 3


def test_outside_window_is_unavailable(tmp_path):
    paths = write_observation(tmp_path, np.full((3, 3), 8000), np.full((3, 3), 2000))
    assert RasterioPointReader().read_observation(paths, -10, 10) is None
