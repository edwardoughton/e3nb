"""
NLOS Demo.

Written by Ed Oughton.

March 2021

"""
import os
import configparser
import random
import glob
import numpy as np
import pandas as pd
import geopandas as gpd

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')
RESULTS = os.path.join(BASE_PATH, '..', 'results')


def lookup_rain_region(rain_regions):
    """
    Find the correct rain region.

    """
    return rain_regions['high']


def lookup_frequency(path_length, frequency_lookup):
    """
    Lookup the maximum allowable operating frequency.

    """
    if path_length < 10000:
        return frequency_lookup['under_10km']
    elif 10000 <= path_length < 20000:
        return frequency_lookup['under_20km']
    elif 20000 <= path_length < 45000:
        return frequency_lookup['under_45km']
    else:
        print('Path_length outside of distance range: {}'.format(path_length))


def check_foliage_presence(routing_structure):
    """
    Check for potential foliage

    """
    #implement landuse layer for probability of foliage
    return 'yes'


def fresnel_clearance_lookup(path_length, frequency, fresnel_lookup):
    """
    Check freznel clearance zone.

    """
    if path_length < 10000:
        data = fresnel_lookup['0_10']
    elif 10000 <= path_length < 25000:
        data = fresnel_lookup['10_25']
    elif 25000 <= path_length < 45000:
        data = fresnel_lookup['25_40']
    else:
        print('Path_length outside of distance range: {}'.format(path_length))

    output = {}

    for key, value in data.items():

        lower = key.split('_')[0]
        upper = key.split('_')[1]

        if int(lower) < frequency <= int(upper):
            output[key] = value

    return output


def generate_path_profile(foliage, clearance, max_antenna_height):
    """
    Generate the path profile. CLOS vs NLOS can be a probability
    based on a lookup table.

    """
    random_number = random.uniform(0, 1)

    if random_number > 0.5:
        return 'CLOS'
    else:
        return 'NLOS'


def estimate_cost(path_length, frequency, cost_by_dist, cost_by_freq):
    """
    Estimate the link cost.

    """
    output = []

    for key, value in cost_by_dist.items():

        lower = int(key.split('_')[0]) * 1e3
        upper = int(key.split('_')[1]) * 1e3

        if int(lower) < path_length <= int(upper):
            output.append({
                'cost_type': 'antenna_{}_m'.format(value['antenna_size_m']),
                'cost_each_usd': value['cost_each_usd'],
                'cost_for_link_usd': value['cost_for_link_usd'],
            })

    for key, value in cost_by_freq.items():

        lower = int(key.split('_')[0])
        upper = int(key.split('_')[1])

        if int(lower) < frequency <= int(upper):
            output.append({
                'cost_type': 'p2p_radio (all-ODU, high-power, licensed-bands)',
                'cost_each_usd': value['cost_each_usd'],
                'cost_for_link_usd': value['cost_for_link_usd'],
            })

    return output

if __name__ == '__main__':

    countries = [
        {'iso3': 'PER', 'iso2': 'PE', 'regional_level': 2,
            # 'max_distance_clos': 40000, 'max_distance_nlos': 1200,
            'max_antenna_height': 30,
            'buffer_size_m': 5000, 'grid_width_m': 1000, 'region': 'SSA',
            'pop_density_km2': 25, 'settlement_size': 500, 'subs_growth': 3.5,
            'smartphone_growth': 5, 'cluster': 'C1', 'coverage_4G': 16
        },
    ]

    rain_regions = {
        'high': 5000, #meters
        'moderate': 10000,
        'low': 15000
    }

    frequency_lookup = {
        'under_10km': 18, #GHz
        'under_20km': 15, #GHz
        'under_45km': 8, #GHz
    }

    fresnel_lookup = {
        '0_10':{ #key is by distance (km)
            #X_Y_ is range freq X to freq Y
            '6_8_nofoliage': 15,
            '6_8_foliage': 25,
            '11_15_nofoliage': 13,
            '11_15_foliage': 23,
            '15_18_nofoliage': 12,
            '15_18_foliage': 22
        },
        '10_25':{
            '6_8_nofoliage': 19,
            '6_8_foliage': 29,
            '11_15_nofoliage': 16,
            '11_15_foliage': 26,
            '15_18_nofoliage': 13,
            '15_18_foliage': 23
        },
        '25_40':{
            '6_8_nofoliage': 19,
            '6_8_foliage': 29,
            '11_15_nofoliage': 16,
            '11_15_foliage': 26,
            '15_18_nofoliage': 13,
            '15_18_foliage': 23
        },
    }

    cost_dist = {
        '0_10': {
            'antenna_size_m': 0.6,
            'cost_each_usd': 300,
            'cost_for_link_usd': 600,
        },
        '10_20': {
            'antenna_size_m': 0.9,
            'cost_each_usd': 600,
            'cost_for_link_usd': 1200,
        },
        '20_30': {
            'antenna_size_m': 1.2,
            'cost_each_usd': 1200,
            'cost_for_link_usd': 2400,
        },
        '30_40': {
            'antenna_size_m': 1.8,
            'cost_each_usd': 2400,
            'cost_for_link_usd': 4800,
        }
    }

    cost_freq = {
        '6_8': {
            'cost_each_usd': 3000,
            'cost_for_link_usd': 6000,
        },
        '11_13': {
            'cost_each_usd': 3000,
            'cost_for_link_usd': 6000,
        },
        '15_18': {
            'cost_each_usd': 3000,
            'cost_for_link_usd': 6000,
        },
    }

    for country in countries:

        iso3 = country['iso3']

        #get the shape paths all buffer routing zones
        path = os.path.join(DATA_INTERMEDIATE, iso3, 'buffer_routing_zones', 'edges')
        all_paths = glob.glob(path + '/*.shp')[:1]

        results = []

        for path in all_paths:

            max_rain_link_dist = lookup_rain_region(rain_regions)

            modeling_region = os.path.basename(path)[:-4] #get the GID ID for the region

            output = []

            routing_structures = gpd.read_file(path, crs='epsg:4326')[:1]

            for idx, routing_structure in routing_structures.iterrows():

                routing_structure = \
                    gpd.GeoDataFrame({'geometry': [routing_structure['geometry']]}, index=[0])
                routing_structure = routing_structure.set_crs('epsg:4326')
                routing_structure = routing_structure.to_crs('epsg:3857')
                routing_structure['length'] = routing_structure['geometry'].length

                path_length = routing_structure['length'].iloc[0]

                if path_length < max_rain_link_dist:

                    frequency = lookup_frequency(path_length, frequency_lookup)

                else:
                    print('Path is over max region allowable length')

                foliage = check_foliage_presence(routing_structure)

                clearance = fresnel_clearance_lookup(path_length, frequency,
                                        fresnel_lookup)

                max_antenna_height = country['max_antenna_height']

                los = generate_path_profile(
                    foliage,
                    clearance,
                    max_antenna_height
                )

                costs = estimate_cost(path_length, frequency, cost_dist, cost_freq)

                results = results + costs

        results = pd.DataFrame(results)

        results.to_csv(os.path.join(RESULTS, iso3, 'results.csv'))
