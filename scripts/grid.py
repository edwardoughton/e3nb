"""
Create 10km x 10km grid using the country shapefile.

Written by Ed Oughton.

"""
import argparse
import os
import configparser
import geopandas as gpd
from shapely.geometry import Polygon, mapping
import pandas as pd
import numpy as np
import rasterio
from rasterstats import zonal_stats

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def generate_grid(region, x_length, y_length):
    """
    Generate a spatial grid of nxn meters for the chosen shape.

    """
    region.crs = "epsg:4326"
    country_outline = region.to_crs("epsg:3857")

    xmin, ymin, xmax, ymax = country_outline.total_bounds

    #10km sides, leading to 100km^2 area
    length = x_length #1e5
    wide = y_length #1e5

    cols = list(range(int(np.floor(xmin)), int(np.ceil(xmax + wide)), int(wide)))
    rows = list(range(int(np.floor(ymin)), int(np.ceil(ymax + length)), int(length)))
    rows.reverse()

    polygons = []
    for x in cols:
        for y in rows:
            polygons.append( Polygon([(x,y), (x+wide, y), (x+wide, y-length), (x, y-length)]))

    #create grid as geopandas dataframe
    grid = gpd.GeoDataFrame({'geometry': polygons}, crs='epsg:3857')

    #add grid id column and copy
    grid['id'] = grid.index

    #copy dataframe and convert to centroids
    centroids = grid.copy()
    centroids['geometry'] = centroids['geometry'].representative_point()

    #get centroids within national boundary and select just id column
    centroids = gpd.overlay(centroids, country_outline, how='intersection')
    centroids = centroids[['id']]

    #get those grid polygons which intersect with centroids
    grid = pd.merge(grid, centroids, on='id', how='inner')

    #convert back to WGS85 and remove null geometries
    grid.crs = "epsg:3857"
    grid = grid.to_crs("epsg:4326")
    grid = grid[grid.geometry.notnull()]

    print('Completed grid generation process')

    return grid


if __name__ == '__main__':

    countries = [
        {'iso3': 'PER', 'iso2': 'PE', 'regional_level': 3, #'regional_nodes_level': 3,
            'region': 'SSA', 'pop_density_km2': 500, 'settlement_size': 1000,
            'subs_growth': 3.5, 'smartphone_growth': 5, 'cluster': 'C1', 'coverage_4G': 16
        },
    ]

    for country in countries:

        generate_grid(country)
