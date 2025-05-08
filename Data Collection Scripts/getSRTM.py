

def get_srtm(country, ee):
    """
    Function to get srtm elevation of country from Earth Engine at 90m resolution
    Args:
        country (str): Country name per ADM0 in GAUL 2015
        ee (obj): initialized Earth Engine object
    """
    srtm = ee.Image("CGIAR/SRTM90_V4")

    # Clip the SRTM data to the boundary of DRC (optional but recommended)
    country_boundary = ee.FeatureCollection("FAO/GAUL_SIMPLIFIED_500m/2015/level0") \
        .filter(ee.Filter.eq('ADM0_NAME', f'{country}'))

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