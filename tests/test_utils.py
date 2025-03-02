import itertools

import dask_image.ndinterp
import xarray
import xarray.testing
from multiscale_spatial_image import MultiscaleSpatialImage
from spatial_image import SpatialImage
from xarray import DataArray

from spatialdata._core.models import get_schema
from spatialdata._core.transformations import Affine
from spatialdata.utils import unpad_raster


def _pad_raster(data: DataArray, axes: tuple[str, ...]) -> DataArray:
    new_shape = tuple([data.shape[i] * (2 if axes[i] != "c" else 1) for i in range(len(data.shape))])
    x = data.shape[axes.index("x")]
    y = data.shape[axes.index("y")]
    affine = Affine(
        [
            [1, 0, -x / 2.0],
            [0, 1, -y / 2.0],
            [0, 0, 1],
        ],
        input_axes=("x", "y"),
        output_axes=("x", "y"),
    )
    matrix = affine.to_affine_matrix(input_axes=axes, output_axes=axes)
    transformed = dask_image.ndinterp.affine_transform(data, matrix, output_shape=new_shape)
    return transformed


def test_unpad_raster(images, labels) -> None:
    for raster in itertools.chain(images.images.values(), labels.labels.values()):
        schema = get_schema(raster)
        if isinstance(raster, SpatialImage):
            data = raster
        elif isinstance(raster, MultiscaleSpatialImage):
            d = dict(raster["scale0"])
            assert len(d) == 1
            data = d.values().__iter__().__next__()
        else:
            raise ValueError(f"Unknown type: {type(raster)}")
        padded = _pad_raster(data.data, data.dims)
        if isinstance(raster, SpatialImage):
            padded = schema.parse(padded, dims=data.dims)
        elif isinstance(raster, MultiscaleSpatialImage):
            # some arbitrary scaling factors
            padded = schema.parse(padded, dims=data.dims, multiscale_factors=[2, 2])
        else:
            raise ValueError(f"Unknown type: {type(raster)}")
        unpadded = unpad_raster(padded)
        if isinstance(raster, SpatialImage):
            xarray.testing.assert_equal(raster, unpadded)
        elif isinstance(raster, MultiscaleSpatialImage):
            d0 = dict(raster["scale0"])
            assert len(d0) == 1
            d1 = dict(unpadded["scale0"])
            assert len(d1) == 1
            xarray.testing.assert_equal(d0.values().__iter__().__next__(), d1.values().__iter__().__next__())
        else:
            raise ValueError(f"Unknown type: {type(raster)}")
