import logging
import os
import yaml
import sys
import ee
import getHealth, cropLCC, getRoads, createConfig
import geemap
from geopandas import read_file


def get_srtm(country, country_bounds, ee_project):
    """
    Function to get srtm elevation of country from Earth Engine at 90m resolution
    Args:
        country (str): Country name per ADM0 in GAUL 2015
        ee (obj): initialized Earth Engine object
    """
    ee.Authenticate()
    ee.Initialize(project=ee_project)
    srtm = ee.Image("CGIAR/SRTM90_V4")

    # Clip the SRTM data to the boundary of DRC (optional but recommended)
    # country_boundary = ee.FeatureCollection("FAO/GAUL_SIMPLIFIED_500m/2015/level0") \
    #     .filter(ee.Filter.eq('ADM0_NAME', f'{country}'))

    gdf = read_file(country_bounds)
    country_boundary = ee.FeatureCollection(geemap.gdf_to_ee(gdf))

    clipped_srtm = srtm.clip(country_boundary)

    # Export the clipped image to your Google Drive
    task = ee.batch.Export.image.toDrive(
        image=clipped_srtm,
        description=f'{country}_DEM_Clip',
        scale=90,
        region=country_boundary.geometry().bounds(),
        maxPixels=1e10
    )
    task.start()
    print("Export task started. Check the Earth Engine console for progress.")

if __name__=='__main__':

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    if os.path.exists(sys.argv[1]):
        with open(sys.argv[1]) as file:
            params = yaml.safe_load(file)

        country = params['Country']
        health_master = params['HealthMaster']
        roads = params['Roads']
        road_costs = params['RoadCosts']
        lcc_master = params['LCCGlobal']
        country_bounds = params['CountryBoundary']
        lcc_out = params['CropLCCPath']
        roads_out = params['RoadsSavePath']
        roads_costs_out = params['RoadsCostsSavePath']
        health_out = params['HealthSavePath']
        ee_project = params['EE Project']
        config_template = params['configTemplate']
        mot_config = params['motorisedConfig']
        walk_config = params['walkingConfig']

        if params['Health']['run']:
            print(f'Subsetting health dataset for {country}')
            df = getHealth.subset_country(country, health_master)
            getHealth.pd_to_gpd(df, health_out)
            print(f'Saved health subset for {country} to {health_out}')
        
        if params['FixRoads']['run']:
            if params['FixRoads']['tags']:
                print(f'Saving road tags')
                getRoads.fixRoads(roads, roads_out)
            if params['FixRoads']['DisplayNewTypes']:
                getRoads.findNewTypes(roads,road_costs_master=road_costs)
            if params['FixRoads']['GetRoadCosts']:
                getRoads.saveRoadCosts(road_costs, roads, roads_costs_out)
            
        if params['CropLCC']['run']:
            print('Cropping Land Cover map')
            cropLCC.crop_tif_w_shp(lcc_master, country_bounds, lcc_out)
            print(f'Saved LCC crop for {country} to {lcc_out}')

        if params['SRTM']['run']:
            print('Preparing to authenticate EE instance')
            print('Sending SRTM DEM task to Google EE')
            get_srtm(country,country_bounds,ee_project)

        if params['createConfig']['run']:
            print('Creating config files')
            createConfig.createConfig(country, config_template, walk_config, mot_config)

    else:
        print('Config file not found')





    

    