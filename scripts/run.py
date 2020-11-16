"""
Run script

"""
import os
import configparser
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
import random

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')
RESULTS = os.path.join(BASE_PATH, '..', 'results')


def run_country(country):
    """

    """
    iso3 = country['iso3']

    folder_out_csv = os.path.join(RESULTS, iso3, 'csv')

    if not os.path.exists(folder_out_csv):
        os.makedirs(folder_out_csv)

    folder_out_shapes = os.path.join(RESULTS, iso3, 'shapes')

    if not os.path.exists(folder_out_shapes):
        os.makedirs(folder_out_shapes)

    path = os.path.join(DATA_INTERMEDIATE, iso3, 'los_lookup')
    all_paths = glob.glob(path + '/*.csv')

    for path in all_paths:

        lookup, unique_sources = load_lookup(path)

        results = find_least_cost_network(lookup, unique_sources, ['los'])

        results_csv = pd.DataFrame(results)

        filename = os.path.basename(path)[:-4] + '.csv'
        results_csv.to_csv(os.path.join(folder_out_csv, filename), index=False)

        results_shapes = write_out_shapes(results)
        results_shapes = gpd.GeoDataFrame.from_features(results_shapes, crs='epsg:3857')

        filename = os.path.basename(path)[:-4] + '.shp'
        results_shapes.to_file(os.path.join(folder_out_shapes, filename))

    return print('Complete')


def load_lookup(path):
    """

    """
    all_data = pd.read_csv(path)
    unique_sources = all_data['source'].unique()#[:10]
    all_data = all_data.to_dict('records')#[:10]

    lookup = {}

    for source in unique_sources:

        data = {}
        los = []
        nlos = []

        for item in all_data:
            if source == item['source']:
                if item['type'] == 'los':
                    los.append((item['sink'], round(item['distance_m'])))
                else:
                    nlos.append((item['sink'], round(item['distance_m'])))

        data['los'] = los
        data['nlos'] = nlos

        lookup[source] = data

    return lookup, unique_sources


def find_least_cost_network(lookup, unique_sources, los_type):
    """
    Cycle through to find the least cost network path.

    """
    iterations = 10

    least_cost = {}

    for i in range(0, iterations):

        iteration_results = []

        seen = set()
        total_distance = 0
        random.shuffle(unique_sources)

        for source in unique_sources:

            if source in seen:
                continue

            for source_key, all_link_options in lookup.items():

                if source == source_key:

                    link_options = get_link_options(all_link_options, los_type, seen)

                    if len(link_options) == 0:
                        continue

                    sink = random.choice(link_options)

                    iteration_results.append({
                        'source': source,
                        'sink': sink[0],
                        'distance': sink[1]
                    })
                    total_distance += int(sink[1])

                    seen.add(source)

        if len(least_cost) == 0:
            least_cost[total_distance] = iteration_results
        else:
            for key in least_cost:
                if int(total_distance) < int(key):
                    least_cost = {}
                    least_cost[total_distance] = iteration_results

    for key, value in least_cost.items():
        network = value

    return network


def get_link_options(all_link_options, los_type, seen):
    """
    Return the link options available given the stated line of sight type.

    """
    options = []

    for key, values in all_link_options.items():
        if key in los_type:
            for item in values:

                if item[0] in seen:
                    continue

                options.append(item)

    return options


def write_out_shapes(results):
    """

    """
    shapes = []

    for item in results:
        shapes.append({
            'geometry': {
                'type': 'LineString',
                'coordinates': ([
                    (float(item['source'].split('_')[0]), float(item['source'].split('_')[1])),
                    (float(item['sink'].split('_')[0]), float(item['sink'].split('_')[1])),
                ])
            },
            'properties': {
                'distance': item['distance'],
            }
        })

    return shapes


if __name__ == '__main__':

    # countries = find_country_list(['Africa'])

    countries = [
        {'iso3': 'PER', 'iso2': 'PE', 'regional_level': 2, #'regional_nodes_level': 3,
            'region': 'SSA', 'pop_density_km2': 25, 'settlement_size': 500,
            'subs_growth': 3.5, 'smartphone_growth': 5, 'cluster': 'C1', 'coverage_4G': 16
        },
    ]

    for country in countries:

        print('Working on {}'.format(country['iso3']))

        run_country(country)
