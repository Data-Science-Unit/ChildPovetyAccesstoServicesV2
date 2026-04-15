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

# Least Cost path utilising scipy
# http://tretherington.blogspot.com/2017/01/least-cost-modelling-with-python-using.html
# https://scikit-image.org/docs/0.7.0/api/skimage.graph.mcp.html

# Import packages
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import logging
import sys
import rioxarray
import xarray
import numpy
from skimage import graph
import geopandas
import random
from .config import CpasConfig


def service_area(cs, startCells):
    """create a grid of access to services"""
    # From the cost-surface create a 'landscape graph' object which can then be
    # analysed using least-cost modelling
    lg = graph.MCP_Geometric(cs.values, sampling=None)
    lcd = xarray.zeros_like(cs, dtype=numpy.float32)
    # Calculate the least-cost distance from the start cell to all other cells
    # [0] is returning the cumulative costs rather than the traceback
    lcd.values = lg.find_costs(starts=startCells)[0]
    return lcd


def find_location_cells(destinations, cs):
    """find cell indices of destination locations

    Parameters
    ----------
    destinations: geopandas data frame containing locations
    cs: costsurface
    """
    start_cells = []
    status = []
    # loop over all destination locations
    longs = cs.get_index('x')
    lats = cs.get_index('y')
    for location in destinations['geometry']:
        idx_i = longs.get_indexer([location.x], method='nearest')[0]
        idx_j = lats.get_indexer([location.y], method='nearest')[0]
        if cs[0, idx_j, idx_i].isnull():
            # if the cell is not valid check neighbouring cells
            alternatives = []
            for j in range(idx_j - 1, idx_j + 2):
                for i in range(idx_i - 1, idx_i + 2):
                    if not cs[0, j, i].isnull():
                        alternatives.append((0, j, i))
            if len(alternatives) > 0:
                # select a random neighbour
                start_cells.append(random.choice(alternatives))
                status.append('m')
            else:
                status.append('i')
        else:
            start_cells.append((0, idx_j, idx_i))
            status.append('v')
    return start_cells, status


def compute_cost_path(csname, dname, invalid_loc, tag='Facility_n'):
    """compute cost paths

    Parameters
    ----------
    csname: name of input costsurface file
    dname: name of file containing destination locations
    invalid_loc: name of file for storing invalid locations
    tag: name of tag that contains the location name
    """
    # import both cost surfaces
    # cost surface
    logging.info('load cost surface')
    costsurface = rioxarray.open_rasterio(csname, masked=True)
    # import destination locations
    destinations = geopandas.read_file(dname)
    if costsurface.rio.crs is not None:
        if destinations.crs is None:
            raise ValueError(
                "Destinations layer has no CRS, but cost surface CRS is defined. "
                "Assign a CRS to destinations before running cpas-path."
            )
        if destinations.crs != costsurface.rio.crs:
            destinations = destinations.to_crs(costsurface.rio.crs)
        minx, miny, maxx, maxy = costsurface.rio.bounds()
        destinations = destinations.cx[minx:maxx, miny:maxy]
    else:
        logging.warning(
            "Cost surface has no CRS metadata. Destination reprojection was skipped; "
            "make sure both layers are already in the same CRS."
        )
    # select destination locations that are valid to use with cost surface
    logging.info('find locations')
    start_cells, status = find_location_cells(destinations, costsurface)
    destinations['status'] = status
    count = destinations.status.value_counts()
    if 'v' in count:
        print(f"found {count['v']} valid locations")
    if 'm' in count:
        print(f"moved {count['m']} locations")
    if 'i' in count:
        print(f"found {count['i']} invalid locations")
    with open(invalid_loc, 'w', encoding='utf-8') as invalid_out:
        for row in destinations[(destinations['status'] == 'i')].itertuples():
            invalid_out.write(f'{row.geometry.x},{row.geometry.y}')
            if hasattr(row, tag):
                invalid_out.write(',"{}"'.format(getattr(row, tag)))
            invalid_out.write('\n')
    if len(start_cells) == 0:
        raise ValueError(
            "No valid start points were found for front propagation. "
            f"Destinations in bounds: {len(destinations)}; invalid: {count.get('i', 0)}. "
            "Check that destination points overlap the cost surface extent and that at least one "
            "point falls on a non-null traversable cell."
        )
    # find costs algorithm does not deal with np.nan so change these
    # to -9999 in cost surface any negative values are ignored
    costsurface = costsurface.fillna(-9999)
    # cs.data = np.where(cs.data != cs.data, -9999, cs.data)
    # calculate the costs for each square in the grid
    logging.info('calculating costs')
    costs = service_area(costsurface, start_cells)
    costs = xarray.where(numpy.isfinite(costs), costs, numpy.nan)
    return costs


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

    # read configuration
    cfg = CpasConfig()
    cfg.read(sys.argv[1])

    logging.info('compute costs with water impassable')
    cp = compute_cost_path(cfg.costsurface, cfg.destinations, cfg.invalid_loc,
                           tag=cfg.destinations_cfg['tag'])
    # repeat the above with water passable cost surface
    logging.info('compute costs with water passable')
    cw = compute_cost_path(cfg.costsurface_water, cfg.destinations,
                           cfg.invalid_loc_water,
                           tag=cfg.destinations_cfg['tag'])

    # bring both access layers together for output
    logging.info('merge cost surface')
    cp = xarray.where(cp.isnull(), cw, cp)

    logging.info('write result')
    cp.rio.to_raster(cfg.cost_path)


if __name__ == "__main__":
    main()
