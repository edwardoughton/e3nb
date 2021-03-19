"""
Convert Modis data from .hdf to .tif

Written by Ed Oughton.

March 2021

"""
import os
import configparser
import rioxarray as rxr
import geopandas as gpd
import numpy as np
import xarray
import glob

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')

path = os.path.join(DATA_RAW, 'modis', '.hdf')
all_paths = glob.glob(path + '/*.hdf')

for path in all_paths:

    print('Working on : {}'.format(path))

    modis_pre = rxr.open_rasterio(path, masked=True)

    filename_out = os.path.basename(path)[:-4] + ".tif"
    path_out = os.path.join(DATA_RAW, 'modis', '.tif', filename_out)
    modis_pre.isel(band=0).rio.to_raster(path_out, crs='epsg:9122')
