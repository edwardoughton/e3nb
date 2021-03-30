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
from shapely.geometry import Point, box, LineString, shape
from rasterstats import gen_zonal_stats

from inputs import countries
from inputs import rain_regions
from inputs import frequency_lookup
from inputs import fresnel_lookup
from inputs import cost_dist
from inputs import cost_freq

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


def load_region_lookup(region_lookup, routing_structures):
    """
    Load the regional lookup data.

    """
    region_ids = routing_structures['regions'].unique()

    for item in region_lookup:
        if item['regions'] == region_ids:
            return item


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
        print('Path_length outside dist range: {}'.format(path_length))


def check_foliage_presence(routing_structure, modis_lookup):
    """
    Check for potential foliage.

    """
    geom = shape(routing_structure['geometry'])
    routing_structure = gpd.GeoDataFrame({'geometry': [geom]}, index=[0], crs='epsg:3857')

    routing_structure['geometry'] = routing_structure['geometry'].to_crs('epsg:4326')

    representative_point = routing_structure['geometry'].representative_point()[0]

    tile_paths = find_correct_tile(representative_point, modis_lookup)

    results = []

    for tile_path in tile_paths:
        stats = next(gen_zonal_stats(
            routing_structure['geometry'],
            tile_path,
            nodata=-9999
        ))

        if not stats['mean'] == None:
            results.append(stats['mean'])

    mean = sum(results) / len(results)

    if mean < 20:
        return 'nofoliage'
    elif mean >= 20:
        return 'foliage'
    else:
        print('Did not recognize zonal stats result')


def find_correct_tile(point, modis_lookup):
    """

    Parameters
    ----------
    point : tuple
        Set of coordinates for the point being queried.
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

    for key, value in modis_lookup.items():

        bbox = box(key[0], key[1], key[2], key[3])

        if bbox.contains(point):
            output.append(value)

    return output


def fresnel_clearance_lookup(path_length, frequency, fresnel_lookup, foliage):
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
        return

    for key, value in data.items():

        if key.split('_')[2] == foliage:
            lower = key.split('_')[0]
            upper = key.split('_')[1]

            if int(lower) < frequency <= int(upper):
                return value
            #do not put an else here
            #let it cycle and it will find the right value


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
            cost_dict = {}
            for k, v in value.items():
                cost_dict['asset_type'] = k
                cost_dict['cost_usd'] = v
            output.append(cost_dict)

    for key, value in cost_by_freq.items():

        lower = int(key.split('_')[0])
        upper = int(key.split('_')[1])

        if int(lower) < frequency <= int(upper):
            cost_dict = {}
            for k, v in value.items():
                cost_dict['asset_type'] = k
                cost_dict['cost_usd'] = v
            output.append(cost_dict)

    return output


def load_modis_tile_lookup(country):
    """
    Load in the preprocessed modis tile lookup.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    """
    iso3 = country['iso3']

    path = os.path.join(DATA_INTERMEDIATE, iso3, 'modis_lookup.csv')
    data = pd.read_csv(path)
    data = data.to_records('dicts')

    lookup = {}

    for item in data:

        coords = (item['x1'], item['y1'], item['x2'], item['y2'])

        lookup[coords] = item['path']

    return lookup


def aggregate_results(results):
    """

    """
    output = []

    all_areas = set()

    for item in results:
        all_areas.add(item['modeling_region'])

    for area in list(all_areas):

        cost = 0
        total_path_length = 0

        for item in results:
            if area == item['modeling_region']:

                modeling_region = item['modeling_region']
                regions = item['regions']
                population = item['population']
                area_m = item['area_m']
                pop_density_km2= item['pop_density_km2']

                total_path_length += item['path_length']
                cost += item['cost_usd']

        output.append({
            'modeling_region': modeling_region,
            'regions': regions,
            'population': population,
            'area_m': area_m,
            'pop_density_km2': pop_density_km2,
            'total_path_length': total_path_length,
            'cost_usd': cost,
        })

    return output


def get_settlement_results(results, settlements):
    """

    """
    output = []

    regions = set()

    for idx, region in results.iterrows():
        values = region['regions']
        for item in list(values.split('-')):
            regions.add(item)

    for region in regions:
        for idx, item in results.iterrows():
            if region in item['regions']:
                cost_usd = item['cost_usd']

        for idx, item in settlements.iterrows():
            region = region.replace("'", "")
            region2 = '{}'.format(item['GID_2'])

            if region == region2:
                output.append({
                    'id': item['id'],
                    'GID_0': item['GID_0'],
                    'GID_2': item['GID_2'],
                    'population': item['population'],
                    'type': item['type'],
                    'lon': item['lon'],
                    'lat': item['lat'],
                    'cost_per_pop_covered': cost_usd / item['population'],
                })

    return output


if __name__ == '__main__':

    for country in countries:

        iso3 = country['iso3']

        modis_lookup = load_modis_tile_lookup(country)

        filename = 'population_and_terrain_lookup.csv'
        path = os.path.join(DATA_INTERMEDIATE, iso3, filename)
        regional_lookup = pd.read_csv(path)
        regional_lookup = regional_lookup.to_dict('records')

        path = os.path.join(DATA_INTERMEDIATE, iso3, 'buffer_routing_zones', 'edges')
        all_paths = glob.glob(path + '/*.shp')#[:1]

        results = []
        costs_by_settlement = []

        for path in all_paths:

            max_rain_link_dist = lookup_rain_region(rain_regions)

            modeling_region = os.path.basename(path)[:-4] #get the GID ID for the region

            output_shapes = []

            routing_structures = gpd.read_file(path, crs='epsg:4326')#[:1]

            region_info = load_region_lookup(regional_lookup, routing_structures)

            for idx, routing_structure in routing_structures.iterrows():

                routing_structure = \
                    gpd.GeoDataFrame({'geometry': [routing_structure['geometry']]}, index=[0])
                routing_structure = routing_structure.set_crs('epsg:4326')
                routing_structure = routing_structure.to_crs('epsg:3857')
                routing_structure['length'] = routing_structure['geometry'].length

                point_start = routing_structure['geometry'][0].coords[0]
                point_end = routing_structure['geometry'][0].coords[-1]

                all_routes = []

                path_length = routing_structure['length'].iloc[0]

                if path_length < max_rain_link_dist:
                    all_routes.append({
                        'type': 'Feature',
                        'geometry': routing_structure['geometry'][0],
                        'properties': {
                            'length': path_length,
                        },
                    })

                else:
                    while not point_end == point_start:

                        line = LineString([point_start, point_end])

                        intermediate_point = line.interpolate(
                            max_rain_link_dist).coords[0]

                        start = point_start
                        end = intermediate_point

                        all_routes.append({
                            'type': 'Feature',
                            'geometry': {
                                'type': 'LineString',
                                'coordinates': [
                                    [start[0], start[1]],
                                    [end[0], end[1]],
                                    ],
                            },
                            'properties': {
                                'length': LineString([start, end]).length,
                            },
                        })

                        point_start = end

                output_shapes = output_shapes + all_routes

                for item in all_routes:

                    path_length = item['properties']['length']

                    #assumption: longer links to lower frequencies
                    #however, not all frequencies are available in every
                    #link location - need to caveat this
                    #technically logic, but not necessarily a direct regulatory
                    #reflection
                    frequency = lookup_frequency(path_length, frequency_lookup)

                    foliage = check_foliage_presence(item, modis_lookup)

                    clearance = fresnel_clearance_lookup(path_length, frequency,
                                            fresnel_lookup, foliage)

                    #30m is cheap - built freestanding (no guide wire anchors needed)
                    #we might was to build higher towers, all the way up to 50m
                    max_antenna_height = country['max_antenna_height']

                    los = generate_path_profile(
                        foliage,
                        clearance,
                        max_antenna_height
                    )

                    costs = estimate_cost(
                        path_length,
                        frequency,
                        cost_dist,
                        cost_freq,
                    )

                    for cost in costs:
                        results.append({
                            'modeling_region': modeling_region,
                            'regions': region_info['regions'],
                            'population': region_info['population'],
                            'area_m': region_info['area_m'],
                            'pop_density_km2': region_info['pop_density_km2'],
                            'path_length': path_length,
                            'frequency': frequency,
                            'los': los,
                            'foliage': foliage,
                            'clearance': clearance,
                            'max_antenna_height': max_antenna_height,
                            'asset_type': cost['asset_type'],
                            'cost_usd': cost['cost_usd'],
                        })

            output_shapes = gpd.GeoDataFrame.from_features(output_shapes, crs='epsg:3857')

            directory = os.path.join(RESULTS, iso3, 'edges')
            if not os.path.exists(directory):
                os.makedirs(directory)
            filename = os.path.basename(modeling_region)
            output_shapes.to_file(os.path.join(directory, filename + '.shp'))

        ##export aggregated results
        aggregated_results = aggregate_results(results)
        aggregated_results = pd.DataFrame(aggregated_results)
        filename = 'aggregated_results.csv'
        aggregated_results.to_csv(os.path.join(RESULTS, iso3, filename), index=False)

        ##load settlement shapes
        filename = 'settlements.shp'
        directory = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements')
        settlements = gpd.read_file(os.path.join(directory, filename))

        ##export settlement results
        settlement_results = get_settlement_results(aggregated_results, settlements)
        costs_by_settlement = costs_by_settlement + settlement_results

        ##export cost results
        results = pd.DataFrame(results)
        results.to_csv(os.path.join(RESULTS, iso3, 'results.csv'), index=False)

    ##export all final settlement results
    costs_by_settlement = pd.DataFrame(costs_by_settlement)
    filename = 'costs_by_settlement.csv'
    costs_by_settlement.to_csv(os.path.join(RESULTS, iso3, filename), index=False)
