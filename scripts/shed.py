import configparser
import os, sys
import glob
import rasterio as rio
from rasterio.warp import calculate_default_transform, reproject, Resampling
grass7bin = r'"C:\Program Files\GRASS GIS 7.8\grass78.bat"'
os.environ['GRASSBIN'] = grass7bin
os.environ['PATH'] += ';' + r"C:\Program Files\GRASS GIS 7.8\lib"

from grass_session import Session
from grass.script import core as gcore

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

def reproject_raster(in_path, out_path):

    """
    """
    crs = {'init': 'epsg:3857'}
    # reproject raster to project crs
    with rio.open(in_path) as src:
        src_crs = src.crs
        transform, width, height = calculate_default_transform(src_crs, crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()

        kwargs.update({
            'crs': crs,
            'transform': transform,
            'width': width,
            'height': height})

        with rio.open(out_path, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rio.band(src, i),
                    destination=rio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=crs,
                    resampling=Resampling.nearest)
    return(out_path)

# import grass.script as grass
filename = 'S004E026_AVE_DSM.tif' #'S004E027_AVE_DSM.tif'
input_path = os.path.join(BASE_PATH, filename)
output_path = os.path.join(BASE_PATH, 'S004E026_AVE_DSM_reprojected.tif')

reproject_raster(input_path, output_path)

output_dir = os.path.join(BASE_PATH)

gis_path = os.path.join(BASE_PATH, 'test')
# list_of_tiles = ['data/S004E026_AVE_DSM.tif', 'data/S004E027_AVE_DSM.tif']
# list_of_tiles = ['S004E027_AVE_DSM.tif', 'S004E026_AVE_DSM.tif']#,

with Session(gisdb=gis_path, location="location", create_opts="EPSG:3857"):

    print('parse command')
    print(gcore.parse_command("g.gisenv", flags="s", set="DEBUG=3"))

    print('r.external')
    # now link a GDAL supported raster file to a binary raster map layer,
    # from any GDAL supported raster map format, with an optional title.
    # The file is not imported but just registered as GRASS raster map.
    gcore.run_command('r.external', input=output_path, output='test_output', overwrite=True)

    print('r.external.out')
    #write out as geotiff
    gcore.run_command('r.external.out', directory=output_dir, format="GTiff")

    print('r.region')
    #manage the settings of the current geographic region
    gcore.run_command('g.region', raster='test_output')

    print('r.viewshed')
    gcore.run_command('r.viewshed',
            input='test_output',
            output='viewshed.tif',
            coordinate= [2950000, -400000],#[27.5, -3.5],
            obs_elev=1.75,
            tgt_elev=0.0,
            memory=5000,
            overwrite=True,
            quiet=True,
            max_distance=20000,
            verbose=True
    )
    # gcore.run_command('r.external.out', directory=output_dir, format="GTiff")
    # gcore.run_command('r.to.vect', input='test_output', output='test_output.vector', type='area')
