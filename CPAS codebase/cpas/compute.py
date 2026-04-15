# This file is part of cpas.
#
# cpas is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# cpas is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with cpas.  If not, see <https://www.gnu.org/licenses/>.
#
# Copyright (C) 2020 cpas team

import logging
import sys

import rioxarray
import geopandas
import xarray
import numpy
from . import costsurface
from .config import CpasConfig


def pixel_size_meters(reference):
    """Return horizontal pixel size in meters for a raster-like DataArray."""
    res_x = abs(reference.rio.resolution()[0])
    crs = reference.rio.crs
    if crs is not None and crs.is_projected:
        return res_x

    # Geographic CRS: convert degree cell width to meters at raster mid-latitude.
    if 'y' in reference.coords and reference.sizes.get('y', 0) > 0:
        lat = float(reference['y'].mean().item())
    else:
        logging.warning(
            "Could not determine latitude from raster coordinates; using "
            "equator conversion for degree-to-meter conversion."
        )
        lat = 0.0
    meters_per_degree_lon = 111320.0 * numpy.cos(numpy.deg2rad(lat))
    return res_x * max(abs(meters_per_degree_lon), 1.0)


def speed_to_cost(speed, child_impact=1, reference=None):
    """
    convert speed surface to cost surface

    Parameters
    ----------
    speed: object containing the speed surface
          in km/h
    child_impact: factor applied when traveling
          with a child (default=1))

    reference: raster-like object used to infer pixel size in meters.
          If omitted, speed coordinates are used.

    Return
    ------
    cost surface
    """

    # apply child impact factor and convert to m/s
    cost = speed * child_impact * 1000 / 3600
    if reference is None:
        reference = speed
    # compute the costsurface, ie time.
    return pixel_size_meters(reference) / cost


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

    cfg = CpasConfig()
    cfg.read(sys.argv[1])

    # load the landcover - speedmap and the landcover dataset
    lc_speedmap = costsurface.readLandcoverSpeedMap(
        cfg.landcover_ws,
        landcover=cfg.landcover_cfg['landcover_type_column'],
        speed=cfg.landcover_cfg['speed_column']
    )
    logging.info('loading landcovers')
    landcover = rioxarray.open_rasterio(cfg.landcover, masked=True)
    # compute the speed surface due to the landcover
    logging.info('constructing landcover speed cost surface')
    lws = costsurface.applyLandcoverSpeedMap(landcover, lc_speedmap)

    # load the road - speedmap and the road dataset
    r_speedmap = costsurface.readRoadSpeedMap(
        cfg.roads_ws,
        road=cfg.roads_cfg['road_type_column'],
        speed=cfg.roads_cfg['speed_column']
    )
    logging.info('loading roads')
    roads = geopandas.read_file(cfg.roads)
    if landcover.rio.crs is not None:
        if roads.crs is None:
            raise ValueError(
                "Roads layer has no CRS, but landcover CRS is defined. "
                "Assign a CRS to roads before running cpas-compute."
            )
        if roads.crs != landcover.rio.crs:
            roads = roads.to_crs(landcover.rio.crs)
    roads = roads.iterfeatures()
    logging.info('constructing road speed cost surface')
    rws = costsurface.rasterizeAllRoads(roads, landcover, r_speedmap)

    # compute the slope impact and resample it
    logging.info('loading DEM')
    dem = rioxarray.open_rasterio(cfg.dem,
                                  masked=True).rio.reproject_match(lws)
    logging.info('computing slope')
    slope_impact = costsurface.computeSlopeImpact(dem)
    # make sure coordinates are the same
    # there might be some numerical noise after reprojecting the data
    slope_impact['x'] = lws['x']
    slope_impact['y'] = lws['y']

    # combine the two speed surfaces
    logging.info('combine cost surfaces')
    ws = xarray.where(rws.notnull(), rws, lws)

    # remove some of the large objects to free up some memory
    logging.info('tidy up some space')
    del dem
    del lws
    del rws

    # compute cost surface
    logging.info('constructing cost surface')
    cs = speed_to_cost(ws * slope_impact, cfg.child_impact, reference=landcover)
    if landcover.rio.crs is not None:
        cs = cs.rio.write_crs(landcover.rio.crs, inplace=False)

    # write costsurface
    logging.info('writing cost surface')
    cs.rio.to_raster(cfg.costsurface)

    # consider water being passable
    # 10 is the code for open water
    logging.info('constructing water cost surface')
    water = xarray.where(landcover == 10, cfg.waterspeed, numpy.nan)
    # convert water speed to time
    # 1 as children arnt slower than adults on motor boats...
    water = speed_to_cost(water, reference=landcover)
    cs = xarray.where(water.notnull(), water, cs)
    if landcover.rio.crs is not None:
        cs = cs.rio.write_crs(landcover.rio.crs, inplace=False)

    # write output
    logging.info('writing water cost surface')
    cs.rio.to_raster(cfg.costsurface_water)


if __name__ == '__main__':
    main()
