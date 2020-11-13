"""
This is the runner script for e3nb.

November 2020

Written by Ed Oughton

"""
import os
import csv
import configparser
import pandas as pd
import geopandas as gpd

from grid import generate_grid

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def get_settlement_routing_lookup(path):
    """
    Load settlement routing lookup.

    """
    settlement_routing_lut = pd.read_csv(path, converters={'regions': eval})

    settlement_routing_lut = settlement_routing_lut.to_dict('records')

    output = {}

    for item in settlement_routing_lut:
        output[item['source']] =  item['regions']

    return output


def get_regions_to_model(region_id, GID_level, regions, settlement_routing_lookup):
    """
    Return the regions to model as a geopandas dataframe.

    """
    region_ids_to_model = settlement_routing_lookup[region_id]

    regions_to_model = regions[regions[GID_level].isin(region_ids_to_model)]

    return regions_to_model


if __name__ == '__main__':

    countries = [
        {'iso3': 'PER', 'iso2': 'PE', 'regional_level': 2},
        ]

    for country in countries:

        iso3 = country['iso3']
        GID_level = 'GID_{}'.format(country['regional_level'])

        filename = 'regions_{}_{}.shp'.format(country['regional_level'], iso3)
        path = os.path.join(DATA_INTERMEDIATE, iso3, 'regions', filename)
        regions = gpd.read_file(path, crs='apsg:4326')
        # unique_regions = regions[GID_level].unique()

        filename = 'settlement_routing_lookup.csv'
        path = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure', filename)
        settlement_routing_lookup = get_settlement_routing_lookup(path)

        seen = set()

        for idx, region in regions.iterrows():

            if not region[GID_level] == 'PER.1.4_1': #'PER.6.8_1':
                continue

            if region[GID_level] in seen:
                continue

            regions_to_model = get_regions_to_model(
                region[GID_level],
                GID_level,
                regions,
                settlement_routing_lookup
            )

            unique_regions = str(regions_to_model[GID_level].unique())
            regions_to_model = regions_to_model.copy()
            regions_to_model['modelled_regions'] = unique_regions
            regions_to_model = regions_to_model.dissolve(by='modelled_regions')

            filename = '{}.shp'.format(unique_regions)
            folder = os.path.join(BASE_PATH, '..', 'results', iso3, 'regions')
            path = os.path.join(folder, filename)

            if not os.path.exists(folder):
                os.makedirs(folder)

            regions_to_model.to_file(path, crs='epsg:4326')

            grid = generate_grid(regions_to_model, 20000, 20000)

            output_dir = os.path.join(BASE_PATH, '..', 'results', iso3, 'grid')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            filename = '{}.shp'.format(unique_regions)
            grid.to_file(os.path.join(output_dir, filename))

            seen.update(unique_regions)
