# Copyright Iris contributors
#
# This file is part of Iris and is released under the BSD license.
# See LICENSE in the root of the repository for full licensing details.

"""Unit tests for the `iris.analysis.cartography.area_weights` function."""

import pytest

import iris.analysis.cartography
import iris.tests.stock as stock


class TestInvalidUnits:
    def test_latitude_no_units(self):
        cube = stock.lat_lon_cube()
        cube.coord("longitude").guess_bounds()
        cube.coord("latitude").guess_bounds()
        cube.coord("latitude").units = None
        with pytest.raises(ValueError, match="Units of degrees or radians required"):
            iris.analysis.cartography.area_weights(cube)

    def test_longitude_no_units(self):
        cube = stock.lat_lon_cube()
        cube.coord("latitude").guess_bounds()
        cube.coord("longitude").guess_bounds()
        cube.coord("longitude").units = None
        with pytest.raises(ValueError, match="Units of degrees or radians required"):
            iris.analysis.cartography.area_weights(cube)


def test_multi_coord():
    # Confirm the correct handling of multiple latitude and longitude coordinates.
    #  I.e. it doesn't crash - it has a mechanism for choosing the one that won't crash
    #   (only the DimCoord is 1D).
    cube = stock.realistic_4d_w_everything()
    assert cube.coord("grid_latitude", dim_coords=True)
    assert cube.coord("grid_longitude", dim_coords=True)
    assert cube.coord("latitude", dim_coords=False)
    assert cube.coord("longitude", dim_coords=False)
    _ = iris.analysis.cartography.area_weights(cube)
