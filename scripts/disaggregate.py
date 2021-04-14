"""
Disaggregate to GID_3 level.

Written by Ed Oughton.

April 2021.

"""
import os
import configparser
import random
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, box, LineString, shape
from shapely.ops import transform
from rasterstats import gen_zonal_stats
import rasterio
import pyproj
# from rasterio.warp import calculate_default_transform, reproject, Resampling
# from rasterio.mask import mask
from rasterstats import zonal_stats, gen_zonal_stats

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')
RESULTS = os.path.join(BASE_PATH, '..', 'results')


def load_raster_tile_lookup(iso3):
    """
    Load in the preprocessed raster tile lookup.

    Parameters
    ----------
    iso3 : string
        Country iso3 code.

    Returns
    -------
    lookup : dict
        A lookup table containing raster tile boundary coordinates
        as the keys, and the file paths as the values.

    """
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'raster_lookup.csv')
    data = pd.read_csv(path)
    data = data.to_records('dicts')

    lookup = {}

    for item in data:

        coords = (item['x1'], item['y1'], item['x2'], item['y2'])

        lookup[coords] = item['path']

    return lookup


def load_settlement_costs(iso3):
    """

    """
    path = os.path.join(RESULTS, iso3, 'costs_by_settlement.csv')
    settlement_costs = pd.read_csv(path)

    output = []

    for idx, settlement in settlement_costs.iterrows():
        output.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': (settlement['lon'], settlement['lat'])
            },
            'properties': {
                'strategy': settlement['strategy'],
                'GID_0': settlement['GID_0'],
                'GID_id': settlement['GID_id'],
                'modeling_region': settlement['modeling_region'],
                'names': settlement['names'],
                'population': settlement['population'],
                'type': settlement['type'],
                'id_range_m': settlement['id_range_m'],
                'cost_per_pop_covered': settlement['cost_per_pop_covered'],
                'cost_per_settlement': settlement['cost_per_settlement'],
                'lon': settlement['lon'],
                'lat': settlement['lat'],
            }
        })

    output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

    return output


def disaggregate(iso3, settlements, tile_lookup):
    """

    """
    output = []

    path_settlements = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements.tif')

    filename = 'settlements.shp'
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements', filename)
    all_settlements = gpd.read_file(path, crs='epsg:4326')#[:1]
    all_settlements['geometry'] = all_settlements['geometry'].to_crs('epsg:3857')
    all_settlements['geometry'] = all_settlements['geometry'].buffer(10)
    all_settlements['geometry'] = all_settlements['geometry'].to_crs('epsg:4326')

    filename = 'regions_3_{}.shp'.format(iso3)
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'regions', filename)
    regions = gpd.read_file(path, crs='epsg:4326')#[:50]

    for idx, region in regions.iterrows():

        # if not region['GID_3'] == 'PER.21.8.6_1':
        #     continue

        if region['geometry'].type == 'Polygon':
            geo_df = gpd.GeoDataFrame({'geometry': region['geometry']},
                index=[0], crs='epsg:4326')
        else:
            geo_df = gpd.GeoDataFrame({'geometry': region['geometry']},
                crs='epsg:4326')

        region_settlements = gpd.overlay(all_settlements, geo_df, how='intersection')

        # all_settlements_pop = 0
        # for idx, item in region_settlements.iterrows():
        #     geom = item['geometry'].representative_point()
        #     name = '{}_{}'.format(geom.x, geom.y)
        #     if name not in list(seen):
        #         all_settlements_pop += item['population']
        #         seen.add(name)

        # if len(region_settlements) > 0:
        #     region_settlements['geometry'] = region_settlements['geometry'].representative_point()
        #     region_settlements.to_file(os.path.join(RESULTS, iso3,
        #         region['GID_3'] + '.shp'), crs='epsg:4326')
        all_settlements_pop = region_settlements['population'].sum()

        area_km2 = get_area(region)

        path_input = find_correct_raster_tile(region['geometry'].bounds, tile_lookup)

        stats = next(gen_zonal_stats(
            region['geometry'],
            path_input,
            add_stats={
                'interdecile_range': interdecile_range
            },
            nodata=0
        ))

        id_range_m = stats['interdecile_range']

        with rasterio.open(path_settlements) as src:

            affine = src.transform
            array = src.read(1)
            array[array <= 0] = 0

            population = [d['sum'] for d in zonal_stats(
                region['geometry'],
                array,
                stats=['sum'],
                nodata=0,
                affine=affine
                )][0]

        if not population == None:
            if population > 0:
                pop_density_km2 = population / area_km2
            else:
                pop_density_km2 = 0
        else:
            population = 0
            pop_density_km2 = 0

        if region['geometry'].type == 'Polygon':
            region_geom = gpd.GeoDataFrame({'geometry': region['geometry']},
                index=[0], crs='epsg:4326')
        else:
            region_geom = gpd.GeoDataFrame({'geometry': region['geometry']},
                crs='epsg:4326')

        covered_settlements = gpd.overlay(settlements, region_geom, how='intersection')

        if len(covered_settlements) == 0:
            continue

        for idx, settlement in covered_settlements.iterrows():
            output.append({
                'strategy': settlement['strategy'],
                'GID_0': settlement['GID_0'],
                'GID_3': region['GID_3'],
                'GID_id': settlement['GID_id'],
                'modeling_region': settlement['modeling_region'],
                'names': settlement['names'],
                'population': population,
                'area_km2': area_km2,
                'pop_density_km2': pop_density_km2,
                'type': settlement['type'],
                'settlement_pop': settlement['population'],
                'all_settlements_pop': all_settlements_pop,
                'id_range_m': id_range_m,
                'cost_per_pop_covered': settlement['cost_per_pop_covered'],
                'cost_per_settlement': settlement['cost_per_settlement'],
                'lon': settlement['lon'],
                'lat': settlement['lat'],
            })

    output = pd.DataFrame(output)
    output = output.drop_duplicates(subset=['strategy','lon', 'lat'])
    path = os.path.join(RESULTS, iso3, 'gid_3_settlement_costs.csv')
    output.to_csv(path, index=False)

    return output


def get_area(modeling_region):
    """
    Return the area in square km.

    Parameters
    ----------
    modeling_region : series
        The modeling region that we wish to find the area for.

    """
    project = pyproj.Transformer.from_crs('epsg:4326', 'esri:54009',
        always_xy=True).transform
    new_geom = transform(project, modeling_region['geometry'])
    area_km2 = new_geom.area / 1e6

    return area_km2


def find_correct_raster_tile(polygon, tile_lookup):
    """

    Parameters
    ----------
    polygon : tuple
        The bounds of the modeling region.
    tile_lookup : dict
        A lookup table containing raster tile boundary coordinates
        as the keys, and the file paths as the values.

    Return
    ------
    output : list
        Contains the file path to the correct raster tile. Note:
        only the first element is returned and if there are more than
        one paths, an error is returned.

    """
    output = []

    poly_bbox = box(polygon[0], polygon[1], polygon[2], polygon[3])

    for key, value in tile_lookup.items():

        bbox = box(key[0], key[1], key[2], key[3])

        if bbox.intersects(poly_bbox):
            output.append(value)

    if len(output) == 1:
        return output[0]
    elif len(output) > 1:
        print('Problem with find_correct_raster_tile returning more than 1 path')
        return output[0]
    else:
        print('Problem with find_correct_raster_tile: Unable to find raster path')


def interdecile_range(x):
    """
    Get range between bottom 10% and top 10% of values.

    This is from the Longley-Rice Irregular Terrain Model.

    Code here: https://github.com/edwardoughton/itmlogic
    Paper here: https://joss.theoj.org/papers/10.21105/joss.02266.pdf

    Parameters
    ----------
    x : list
        Terrain profile values.

    Returns
    -------
    interdecile_range : int
        The terrain irregularity parameter.

    """
    q90, q10 = np.percentile(x, [90, 10])

    interdecile_range = int(round(q90 - q10, 0))

    return interdecile_range


def aggregate_to_regions(iso3):
    """

    """
    output = []

    path = os.path.join(RESULTS, iso3, 'gid_3_settlement_costs.csv')
    data = pd.read_csv(path)#[:100]

    regions = set()
    strategies = set()

    for idx, item in data.iterrows():
        regions.add(item['GID_3'])
        strategies.add(item['strategy'])

    for region in list(regions):
        for strategy in list(strategies):

            covered_population = 0
            uncovered_population = 0
            cost_usd = 0
            attributes = {}

            for idx, item in data.iterrows():
                if region == item['GID_3'] and strategy == item['strategy']:

                    if item['cost_per_settlement'] > 0:
                        covered_population += item['settlement_pop']
                        cost_usd += item['cost_per_settlement']
                    else:
                        uncovered_population += item['settlement_pop']

                    attributes['names'] = item['names']
                    attributes['population'] = item['population']
                    attributes['area_km2'] = item['area_km2']
                    attributes['pop_density_km2'] = item['pop_density_km2']
                    attributes['all_settlements_pop'] = item['all_settlements_pop']
                    attributes['id_range_m'] = item['id_range_m']

            if len(attributes) == 0:
                continue
            # print(attributes['all_settlements_pop'], covered_population)
            output.append({
                'strategy': strategy,
                'GID_0': iso3,
                'GID_3': region,
                'names': attributes['names'],
                'population': attributes['population'],
                'area_km2': attributes['area_km2'],
                'pop_density_km2': attributes['pop_density_km2'],
                'id_range_m': attributes['id_range_m'],
                'covered_population': covered_population,
                'uncovered_population': uncovered_population,#attributes['all_settlements_pop'] - covered_population,
                'cost_usd': cost_usd,
            })

    output = pd.DataFrame(output)
    path = os.path.join(RESULTS, iso3, 'gid_3_aggregated_costs.csv')
    output.to_csv(path, index=False)

    return


if __name__ == "__main__":

    countries = [
        {
            'iso3': 'PER', 'iso2': 'PE', 'regional_level': 2,
            'lowest_regional_level': 3, 'region': 'LAT',
            'pop_density_km2': 100, 'settlement_size': 100,
            'main_settlement_size': 20000, 'subs_growth': 3.5,
            'smartphone_growth': 5, 'cluster': 'C1', 'coverage_4G': 16
        },
        {
            'iso3': 'IDN', 'iso2': 'ID', 'regional_level': 2,
            'lowest_regional_level': 3, 'region': 'SEA',
            'pop_density_km2': 100, 'settlement_size': 100,
            'main_settlement_size': 20000,  'subs_growth': 3.5,
            'smartphone_growth': 5, 'cluster': 'C1', 'coverage_4G': 16
        },
    ]

    for country in countries:

        iso3 = country['iso3']

        print('--Working on {}'.format(iso3))

        tile_lookup = load_raster_tile_lookup(iso3)

        settlements = load_settlement_costs(iso3)

        disaggregate(iso3, settlements, tile_lookup)

        aggregate_to_regions(iso3)
