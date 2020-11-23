"""
Collect results and process into .csv

Written by Ed Oughton

November 2020

"""
import os
import configparser
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
from tqdm import tqdm

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')
RESULTS = os.path.join(BASE_PATH, '..', 'results')


def collect_results(country):
    """
    Load in results.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    path_settlements = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements', 'settlements.shp')
    settlements = gpd.read_file(path_settlements, crs='epsg:4382')
    settlements['geometry'] = settlements['geometry'].to_crs(crs='epsg:3857')

    path_results = os.path.join(RESULTS, iso3, 'shapes')

    paths = glob.glob(os.path.join(path_results, '*nodes.shp'))#[:2]

    output = []

    for path in tqdm(paths):

        modeling_region = os.path.basename(path)[:-4].split('-')[0]

        strategy = os.path.basename(path).split('-')[1]

        network = gpd.read_file(path, crs='epsg:4326')

        network['geometry'] = network['geometry'].to_crs(crs='epsg:3857')

        site_cost = 100000
        network_cost = site_cost * len(network)

        settlements_covered = get_settlements_covered(country, settlements, modeling_region)

        population_covered = 0
        # regions_covered = set()

        for idx, item in settlements_covered.iterrows():
            population_covered += int(item['population'])
            # regions_covered.add(item[GID_level])

        if population_covered > 0 :
            cost_per_pop = network_cost / population_covered
        else:
            cost_per_pop = 0

        output.append({
            'strategy': strategy,
            'population_covered': population_covered,
            'network_towers': len(network),
            'modeling_region': modeling_region,
            # 'regions_covered': list(regions_covered),
            'network_cost': network_cost,
            'cost_per_pop': cost_per_pop,
        })

    output = pd.DataFrame(output)

    path = os.path.join(RESULTS, iso3, 'results.csv')
    output.to_csv(path, index=False)

    return print('Completed results collection')


def get_settlements_covered(country, settlements, modeling_region):
    """
    Find the settlements covered.

    """
    iso3 = country['iso3']

    filename = os.path.join(modeling_region + '.shp')
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'buffer_routing_zones', 'edges', filename)

    buffer_routing_zone = gpd.read_file(path, crs='epsg:4326')

    buffer_routing_zone['geometry'] = buffer_routing_zone['geometry'].to_crs('epsg:3857')

    buffer_routing_zone['geometry'] = buffer_routing_zone['geometry'].buffer(10000)

    settlements_covered = gpd.overlay(settlements, buffer_routing_zone, how='intersection')

    return settlements_covered


if __name__ == '__main__':


    countries = [
        {'iso3': 'PER', 'iso2': 'PE', 'regional_level': 2, #'regional_nodes_level': 3,
            'region': 'SSA', 'pop_density_km2': 25, 'settlement_size': 500,
            'subs_growth': 3.5, 'smartphone_growth': 5, 'cluster': 'C1', 'coverage_4G': 16
        },
    ]

    for country in countries:

        print('Working on {}'.format(country['iso3']))

        collect_results(country)
