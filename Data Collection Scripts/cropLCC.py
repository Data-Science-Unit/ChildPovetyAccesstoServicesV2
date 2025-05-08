import rasterio
from rasterio.mask import mask
from geopandas import read_file

# Open the shapefile
def crop_tif_w_shp(LCCpath, CountryBoundary, OutputPath):
    """
    Crops the Global LCC  using a ADM0 shapefile and saves the result.
    
    Args:
        LCCpath (str): Path to the Global LCC file.
        CountryBoundary (str): Path to the ADM0 boundary for the country.
        OutputPath (str): Path to save the cropped LCC TIFF.
    """
    gdf = read_file(CountryBoundary)

    # Open the raster data
    with rasterio.open(LCCpath) as src:
      # Get data and transform
      data, transform = mask(src, shapes=gdf.geometry, crop=True)

    # Define output details (optional)
    driver = "GTiff"
    height, width = data.shape[1:]

    # Create metadata dictionary
    dst_meta = src.meta.copy()
    dst_meta.update({"driver": driver, "height": height, "width": width, "transform": transform})

    # Save the cropped data as a new .tif file
    with rasterio.open(OutputPath, "w", **dst_meta) as dst:
        dst.write(data)


