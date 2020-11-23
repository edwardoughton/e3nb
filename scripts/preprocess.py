"""
Process settlement layer

"""
import os
import configparser
import json
import math
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Polygon, MultiPoint, MultiPolygon, shape, mapping
from shapely.ops import unary_union, nearest_points #transform,
import rasterio
import networkx as nx
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.mask import mask
from rasterstats import zonal_stats

grass7bin = r'"C:\Program Files\GRASS GIS 7.8\grass78.bat"'
os.environ['GRASSBIN'] = grass7bin
os.environ['PATH'] += ';' + r"C:\Program Files\GRASS GIS 7.8\lib"

from grass_session import Session
from grass.script import core as gcore

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, 'raw')
DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def find_country_list(continent_list):
    """
    This function produces country information by continent.

    Parameters
    ----------
    continent_list : list
        Contains the name of the desired continent, e.g. ['Africa']

    Returns
    -------
    countries : list of dicts
        Contains all desired country information for countries in
        the stated continent.

    """
    print('----')
    print('Loading all countries')
    path = os.path.join(DATA_RAW, 'gadm36_levels_shp', 'gadm36_0.shp')
    countries = gpd.read_file(path)

    print('Adding continent information to country shapes')
    glob_info_path = os.path.join(DATA_RAW, 'global_information.csv')
    load_glob_info = pd.read_csv(glob_info_path, encoding = "ISO-8859-1")
    countries = countries.merge(load_glob_info, left_on='GID_0',
        right_on='ISO_3digit')

    subset = countries.loc[countries['continent'].isin(continent_list)]

    countries = []

    for index, country in subset.iterrows():

        if country['GID_0'] in ['LBY', 'ESH']:
            continue

        if country['GID_0'] in ['LBY', 'ESH'] :
            regional_level =  1
        else:
            regional_level = 2

        countries.append({
            'country_name': country['country'],
            'iso3': country['GID_0'],
            'iso2': country['ISO_2digit'],
            'regional_level': regional_level,
        })

    return countries


def process_country_shapes(country):
    """
    Creates a single national boundary for the desired country.

    Parameters
    ----------
    country : string
        Three digit ISO country code.

    """
    print('----')

    iso3 = country['iso3']

    path = os.path.join(DATA_INTERMEDIATE, iso3)

    if os.path.exists(os.path.join(path, 'national_outline.shp')):
        return 'Completed national outline processing'

    if not os.path.exists(path):
        print('Creating directory {}'.format(path))
        os.makedirs(path)

    shape_path = os.path.join(path, 'national_outline.shp')

    print('Loading all country shapes')
    path = os.path.join(DATA_RAW, 'gadm36_levels_shp', 'gadm36_0.shp')
    countries = gpd.read_file(path)

    print('Getting specific country shape for {}'.format(iso3))
    single_country = countries[countries.GID_0 == iso3]

    print('Excluding small shapes')
    single_country['geometry'] = single_country.apply(
        exclude_small_shapes, axis=1)

    print('Adding ISO country code and other global information')
    glob_info_path = os.path.join(DATA_RAW, 'global_information.csv')
    load_glob_info = pd.read_csv(glob_info_path, encoding = "ISO-8859-1")
    single_country = single_country.merge(
        load_glob_info,left_on='GID_0', right_on='ISO_3digit')

    print('Exporting processed country shape')
    single_country.to_file(shape_path, driver='ESRI Shapefile')

    return print('Processing country shape complete')


def process_regions(country):
    """
    Function for processing the lowest desired subnational regions for the
    chosen country.

    Parameters
    ----------
    country : string
        Three digit ISO country code.

    """
    regions = []

    iso3 = country['iso3']
    level = country['regional_level']

    for regional_level in range(1, level + 1):

        filename = 'regions_{}_{}.shp'.format(regional_level, iso3)
        folder = os.path.join(DATA_INTERMEDIATE, iso3, 'regions')
        path_processed = os.path.join(folder, filename)

        if os.path.exists(path_processed):
            continue

        print('----')
        print('Working on {} level {}'.format(iso3, regional_level))

        if not os.path.exists(folder):
            os.mkdir(folder)

        filename = 'gadm36_{}.shp'.format(regional_level)
        path_regions = os.path.join(DATA_RAW, 'gadm36_levels_shp', filename)
        regions = gpd.read_file(path_regions)

        print('Subsetting {} level {}'.format(iso3, regional_level))
        regions = regions[regions.GID_0 == iso3]

        print('Excluding small shapes')
        regions['geometry'] = regions.apply(exclude_small_shapes, axis=1)

        try:
            print('Writing global_regions.shp to file')
            regions.to_file(path_processed, driver='ESRI Shapefile')
        except:
            print('Unable to write {}'.format(filename))
            pass

    print('Completed processing of regional shapes level {}'.format(level))

    return print('Complete')


def process_settlement_layer(country):
    """
    Clip the settlement layer to the chosen country boundary and place in
    desired country folder.

    Parameters
    ----------
    country : string
        Three digit ISO country code.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']

    path_settlements = os.path.join(DATA_RAW,'settlement_layer',
        'ppp_2020_1km_Aggregated.tif')

    settlements = rasterio.open(path_settlements, 'r+')
    settlements.nodata = 255
    settlements.crs = {"init": "epsg:4326"}

    iso3 = country['iso3']
    path_country = os.path.join(DATA_INTERMEDIATE, iso3,
        'national_outline.shp')

    if os.path.exists(path_country):
        country = gpd.read_file(path_country)
    else:
        print('Must generate national_outline.shp first' )

    path_country = os.path.join(DATA_INTERMEDIATE, iso3)
    shape_path = os.path.join(path_country, 'settlements.tif')

    if os.path.exists(shape_path):
        return print('Completed settlement layer processing')

    print('----')
    print('Working on {} level {}'.format(iso3, regional_level))

    bbox = country.envelope
    geo = gpd.GeoDataFrame()

    geo = gpd.GeoDataFrame({'geometry': bbox})

    coords = [json.loads(geo.to_json())['features'][0]['geometry']]

    #chop on coords
    out_img, out_transform = mask(settlements, coords, crop=True)

    # Copy the metadata
    out_meta = settlements.meta.copy()

    out_meta.update({"driver": "GTiff",
                    "height": out_img.shape[1],
                    "width": out_img.shape[2],
                    "transform": out_transform,
                    "crs": 'epsg:4326'})

    with rasterio.open(shape_path, "w", **out_meta) as dest:
            dest.write(out_img)

    return print('Completed processing of settlement layer')


def exclude_small_shapes(x):
    """
    Remove small multipolygon shapes.

    Parameters
    ---------
    x : polygon
        Feature to simplify.

    Returns
    -------
    MultiPolygon : MultiPolygon
        Shapely MultiPolygon geometry without tiny shapes.

    """
    # if its a single polygon, just return the polygon geometry
    if x.geometry.geom_type == 'Polygon':
        return x.geometry

    # if its a multipolygon, we start trying to simplify
    # and remove shapes if its too big.
    elif x.geometry.geom_type == 'MultiPolygon':

        area1 = 0.01
        area2 = 50

        # dont remove shapes if total area is already very small
        if x.geometry.area < area1:
            return x.geometry
        # remove bigger shapes if country is really big

        if x['GID_0'] in ['CHL','IDN']:
            threshold = 0.01
        elif x['GID_0'] in ['RUS','GRL','CAN','USA']:
            threshold = 0.01

        elif x.geometry.area > area2:
            threshold = 0.1
        else:
            threshold = 0.001

        # save remaining polygons as new multipolygon for
        # the specific country
        new_geom = []
        for y in x.geometry:
            if y.area > threshold:
                new_geom.append(y)

        return MultiPolygon(new_geom)


def generate_settlement_lut(country):
    """
    Generate a lookup table of settlements.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements')
    if not os.path.exists(folder):
        os.makedirs(folder)
    path_output = os.path.join(folder, 'settlements.shp')

    if os.path.exists(path_output):
        return print('settlement processing has already completed')

    print('Working on {} settlement lookup table'.format(iso3))

    filename = 'regions_{}_{}.shp'.format(regional_level, iso3)
    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path, crs="epsg:4326")

    path_settlements = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements.tif')
    settlements = rasterio.open(path_settlements, 'r+')
    settlements.nodata = 255
    settlements.crs = {"init": "epsg:4326"}

    folder_tifs = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements', 'tifs')
    if not os.path.exists(folder_tifs):
        os.makedirs(folder_tifs)

    for idx, region in regions.iterrows():

        # if not region['GID_2'] == ['PER.1.1_1']: #single_region:
        #     continue

        bbox = region['geometry'].envelope
        geo = gpd.GeoDataFrame()
        geo = gpd.GeoDataFrame({'geometry': bbox}, index=[idx])
        coords = [json.loads(geo.to_json())['features'][0]['geometry']]

        #chop on coords
        out_img, out_transform = mask(settlements, coords, crop=True)

        # Copy the metadata
        out_meta = settlements.meta.copy()

        out_meta.update({"driver": "GTiff",
                        "height": out_img.shape[1],
                        "width": out_img.shape[2],
                        "transform": out_transform,
                        "crs": 'epsg:4326'})

        path_output = os.path.join(folder_tifs, region[GID_level] + '.tif')

        with rasterio.open(path_output, "w", **out_meta) as dest:
                dest.write(out_img)

    print('Completed settlement.tif regional segmentation')

    nodes = find_nodes(country, regions)

    # if len(missing_nodes) > 0:
    #     nodes = nodes + missing_nodes

    nodes = gpd.GeoDataFrame.from_features(nodes, crs='epsg:4326')

    bool_list = nodes.intersects(regions['geometry'].unary_union)
    nodes = pd.concat([nodes, bool_list], axis=1)
    nodes = nodes[nodes[0] == True].drop(columns=0)

    settlements = []

    print('Identifying settlements')
    for idx1, region in regions.iterrows():

        # if not region['GID_2'] in single_region:
        #     continue

        seen = set()
        for idx2, node in nodes.iterrows():
            if node['geometry'].intersects(region['geometry']):
                if node['sum'] > 0:
                    settlements.append({
                        'type': 'Feature',
                        'geometry': mapping(node['geometry']),
                        'properties': {
                            'id': idx1,
                            'GID_0': region['GID_0'],
                            GID_level: region[GID_level],
                            'population': node['sum'],
                            'type': node['type'],
                        }
                    })
                    seen.add(region[GID_level])

    settlements = gpd.GeoDataFrame.from_features(
            [
                {
                    'geometry': item['geometry'],
                    'properties': {
                        'id': item['properties']['id'],
                        'GID_0':item['properties']['GID_0'],
                        GID_level: item['properties'][GID_level],
                        'population': item['properties']['population'],
                        'type': item['properties']['type'],
                    }
                }
                for item in settlements
            ],
            crs='epsg:4326'
        )

    settlements['lon'] = round(settlements['geometry'].x, 5)
    settlements['lat'] = round(settlements['geometry'].y, 5)

    settlements = settlements.drop_duplicates(subset=['lon', 'lat'])

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements')
    path_output = os.path.join(folder, 'settlements' + '.shp')
    settlements.to_file(path_output)

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')

    if not os.path.exists(folder):
        os.makedirs(folder)

    path_output = os.path.join(folder, 'main_nodes' + '.shp')
    main_nodes = settlements.loc[settlements['population'] >= 20000]
    main_nodes.to_file(path_output)

    settlements = settlements[['lon', 'lat', GID_level, 'population', 'type']]
    settlements.to_csv(os.path.join(folder, 'settlements.csv'), index=False)

    return print('settlements layer complete')


def find_nodes(country, regions):
    """
    Find key nodes.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    threshold = country['pop_density_km2']
    settlement_size = country['settlement_size']

    folder_tifs = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements', 'tifs')

    interim = []

    print('Working on gathering data from regional rasters')
    for idx, region in regions.iterrows():

        # if not region['GID_2'] == ['PER.1.1_1']:
        #     continue

        path = os.path.join(folder_tifs, region[GID_level] + '.tif')

        with rasterio.open(path) as src: # convert raster to pandas geodataframe
            data = src.read()
            data[data < threshold] = 0
            data[data >= threshold] = 1
            polygons = rasterio.features.shapes(data, transform=src.transform)
            shapes_df = gpd.GeoDataFrame.from_features(
                [{'geometry': poly, 'properties':{'value':value}}
                    for poly, value in polygons if value > 0], crs='epsg:4326'
            )

        geojson_region = [
            {'geometry': region['geometry'],
            'properties': {GID_level: region[GID_level]}
            }]

        gpd_region = gpd.GeoDataFrame.from_features(
                [{'geometry': poly['geometry'],
                    'properties':{GID_level: poly['properties'][GID_level]}}
                    for poly in geojson_region
                ], crs='epsg:4326'
            )

        if len(shapes_df) == 0:
            continue

        nodes = gpd.overlay(shapes_df, gpd_region, how='intersection')

        results = []

        for idx, node in nodes.iterrows():
            pop = zonal_stats(node['geometry'], path, stats=['sum'])
            if not pop[0]['sum'] == None and pop[0]['sum'] > settlement_size:
                results.append({
                    'geometry': node['geometry'],
                    'properties': {
                        '{}'.format(GID_level): node[GID_level],
                        'sum': pop[0]['sum']
                    },
                })

        nodes = gpd.GeoDataFrame.from_features(
            [{
                'geometry': item['geometry'],
                'properties': {
                        '{}'.format(GID_level): item['properties'][GID_level],
                        'sum': item['properties']['sum'],
                    },
                }
                for item in results
            ],
            crs='epsg:4326'
        )

        nodes = nodes.drop_duplicates()

        if len(nodes) == 0:
            continue

        nodes.loc[(nodes['sum'] >= 20000), 'type'] = '>20k'
        nodes.loc[(nodes['sum'] <= 10000) | (nodes['sum'] < 20000), 'type'] = '10-20k'
        nodes.loc[(nodes['sum'] <= 5000) | (nodes['sum'] < 10000), 'type'] = '5-10k'
        nodes.loc[(nodes['sum'] <= 1000) | (nodes['sum'] < 5000), 'type'] = '1-5k'
        nodes.loc[(nodes['sum'] <= 500) | (nodes['sum'] < 1000), 'type'] = '0.5-1k'
        nodes.loc[(nodes['sum'] <= 500), 'type'] = '<0.5k'
        nodes = nodes.dropna()

        for idx, item in nodes.iterrows():
            if item['sum'] > 0:
                interim.append({
                        'geometry': item['geometry'].centroid,
                        'properties': {
                            GID_level: region[GID_level],
                            'sum': item['sum'],
                            'type': item['type'],
                        },
                })

    return interim


def find_largest_regional_settlement(country):
    """
    Find the largest settlement in each region as the main regional
    routing node.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
    path_output = os.path.join(folder, 'largest_regional_settlements.shp')

    if os.path.exists(path_output):
        return print('Largest regional settlement layer already exists')

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements')
    path_input = os.path.join(folder, 'settlements' + '.shp')
    nodes = gpd.read_file(path_input, crs='epsg:4326')

    nodes = nodes.loc[nodes.reset_index().groupby([GID_level])['population'].idxmax()]
    nodes.to_file(path_output, crs='epsg:4326')

    return print('Completed largest regional settlement layer')


def get_settlement_routing_paths(country):
    """
    Create settlement routing paths and export as linestrings.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
    path_output = os.path.join(folder, 'settlement_routing.shp')

    # if os.path.exists(path_output):
    #     return print('Settlement routing paths already exist')

    # folder = os.path.join(DATA_INTERMEDIATE, iso3, 'regions')
    # path_input = os.path.join(folder, 'regions_{}_{}.shp'.format(regional_level, iso3))
    # regions = gpd.read_file(path_input, crs='epsg:4326')

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
    path_input = os.path.join(folder, 'largest_regional_settlements.shp')
    regional_nodes = gpd.read_file(path_input, crs='epsg:4326')

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
    path_input = os.path.join(folder, 'main_nodes.shp')
    main_nodes = gpd.read_file(path_input, crs='epsg:4326')

    paths = []

    for idx, regional_node in regional_nodes.iterrows():

        if regional_node['population'] > 20000:
            continue

        nearest = nearest_points(regional_node.geometry, main_nodes.unary_union)[1]

        geom = LineString([
                    (
                        regional_node['geometry'].coords[0][0],
                        regional_node['geometry'].coords[0][1]
                    ),
                    (
                        nearest.coords[0][0],
                        nearest.coords[0][1]
                    ),
                ])

        # nearest = gpd.GeoDataFrame.from_features([{
        #     'geometry': mapping(nearest),
        #     'properties': {}
        # }])

        # region_main = regions[regions.geometry.map(
        #     lambda x: x.intersects(nearest.geometry.any()))]

        paths.append({
            'type': 'LineString',
            'geometry': mapping(geom),
            'properties': {
                'id': idx,
                'source': regional_node[GID_level],
                # 'main_node': region_main[GID_level]
            }
        })

    paths = gpd.GeoDataFrame.from_features(
        [{
            'geometry': item['geometry'],
            'properties': item['properties'],
            }
            for item in paths
        ],
        crs='epsg:4326'
    )

    paths['geometry'] = paths['geometry'].buffer(0.01)

    geoms = paths.geometry.unary_union
    paths = gpd.GeoDataFrame(geometry=[geoms])

    paths = paths.explode().reset_index(drop=True)

    paths.to_file(path_output, crs='epsg:4326')

    return print('Completed settlement routing paths ')


# def get_settlement_routing_lookup(country):
#     """
#     Create settlement routing lookup.

#     """
#     iso3 = country['iso3']
#     regional_level = country['regional_level']
#     GID_level = 'GID_{}'.format(regional_level)

#     folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
#     path_output = os.path.join(folder, 'settlement_routing_lookup.csv')

#     # if os.path.exists(path_output):
#     #     return print('Settlement routing lookup already exists')

#     folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
#     path_input = os.path.join(folder, 'settlement_routing.shp')
#     paths = gpd.read_file(path_input, crs='epsg:4326')#[:1]

#     folder = os.path.join(DATA_INTERMEDIATE, iso3, 'regions')
#     path_input = os.path.join(folder, 'regions_{}_PER.shp'.format(regional_level))
#     regions = gpd.read_file(path_input, crs='epsg:4326')

#     seen = set()
#     output = []

#     for idx, path in paths.iterrows():

#         # seen.add(path['source'])
#         region_intersections = []

#         for idx, region in regions.iterrows():

#             # if not path['source'] == 'PER.17.5_1':
#             #     continue

#             if path['geometry'].intersects(region['geometry']):

#                 region_intersections.append(region[GID_level])
#                 seen.add(region[GID_level])

#         output.append({
#             # 'id': path['id'],
#             # 'source': path['source'],
#             'regions': region_intersections
#             })

#     for idx, region in regions.iterrows():
#         if not region[GID_level] in list(seen):
#             output.append({
#                 # 'id': 'NA',
#                 # 'source': region[GID_level],
#                 'regions': [region[GID_level]],
#                 })

#     output = pd.DataFrame(output)
#     output.to_csv(path_output, index=False)

#     return print('Completed settlement routing lookup')


def create_regions_to_model(country):
    """
    Subset areas to model. Create a union when multiple areas are required.

    """
    iso3 = country['iso3']
    GID_level = 'GID_{}'.format(country['regional_level'])

    filename = 'regions_{}_{}.shp'.format(country['regional_level'], iso3)
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'regions', filename)
    regions = gpd.read_file(path, crs='epsg:4326')
    regions = regions.drop_duplicates()#[:1]

    filename = 'settlement_routing.shp'
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure', filename)
    settlement_routing = gpd.read_file(path, crs='epsg:4326')#[:5]

    seen = set()

    output = []

    for idx, regions_to_model in settlement_routing.iterrows():

        # if not regions_to_model['FID'] == 51:
        #     continue

        regions_to_model = gpd.GeoDataFrame(
            {'geometry': unary_union(regions_to_model['geometry'])},
            crs='epsg:4326', index=[0])

        regions_to_model = regions[regions.geometry.map(
            lambda x: x.intersects(regions_to_model.geometry.any()))]

        if len(regions_to_model) == 0:
            print('no matching')
            continue

        unique_regions = str(regions_to_model[GID_level].unique())
        unique_regions = unique_regions.replace('[', '').replace(']', '').replace(' ', '_')
        regions_to_model = regions_to_model.copy()
        regions_to_model['modeled_regions'] = unique_regions
        regions_to_model = regions_to_model.dissolve(by='modeled_regions')

        output.append({
            'geometry': regions_to_model['geometry'][0],
            'properties': {
                'regions': unique_regions,
            }
        })

        for item in regions_to_model[GID_level].unique():
            seen.add(item)

    for idx, region in regions.iterrows():

        # if region[GID_level] == 'PER.8.9_1':
        #     print(region)

        if not region[GID_level] in list(seen):

            output.append({
                'geometry': region['geometry'],
                'properties': {
                    'regions': region[GID_level],
                }
            })

            seen.add(region[GID_level])

    output = gpd.GeoDataFrame.from_features(output)
    filename = 'modeling_regions.shp'
    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'modeling_regions')

    if not os.path.exists(folder):
        os.makedirs(folder)

    output.to_file(os.path.join(folder, filename), crs='epsg:4326')

    return print('Completed creation of regions to model')


def create_routing_buffer_zone(country):
    """
    Create a routing buffer zone between the major settlements that need connecting.
    A minimum spanning tree is fitted between the desired settlements, with a buffer
    and union consequently added. This provides a routing zone.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'buffer_routing_zones')
    folder_nodes = os.path.join(folder, 'nodes')
    folder_edges = os.path.join(folder, 'edges')

    if not os.path.exists(folder_nodes):
        os.makedirs(folder_nodes)

    if not os.path.exists(folder_edges):
        os.makedirs(folder_edges)

    filename = 'settlements.shp'
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements', filename)
    settlements = gpd.read_file(path, crs='epsg:4326')

    filename = 'modeling_regions.shp'
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'modeling_regions', filename)
    modeling_regions = gpd.read_file(path, crs='epsg:4326')#[:5]

    for idx, region in modeling_regions.iterrows():

        # if os.path.exists(path_edges):
        #     continue

        modeling_region = gpd.GeoDataFrame.from_features([{
            'geometry': mapping(region['geometry']),
            'properties': {
                'regions': region['regions']
            }
        }], crs='epsg:4326')

        nodes = gpd.overlay(settlements, modeling_region, how='intersection')

        main_node = (nodes[nodes['population'] == nodes['population'].max()])

        #export nodes
        path_nodes = os.path.join(folder_nodes, main_node.iloc[0][GID_level] + '.shp')
        nodes.to_file(path_nodes, crs='epsg:4326')

        #export edges
        path_edges = os.path.join(folder_edges, main_node.iloc[0][GID_level] + '.shp')
        fit_edges(path_nodes, path_edges)

        # if os.path.exists(path_edges):
        #     edges = gpd.read_file(path_edges, crs='epsg:4326')

        #     #export buffer
        #     edges = edges.to_crs("epsg:3857")
        #     edges = edges['geometry'].buffer(20000)

        #     # edges['geometry'] = unary_union(edges)

        #     # edges = edges.set_crs(epsg=3857, inplace=True)
        #     buffer_zone = gpd.GeoDataFrame({'geometry': unary_union(edges)}, crs='epsg:3857', index=[0])

        #     buffer_zone = buffer_zone.to_crs("epsg:4326")
        #     filename = os.path.join(folder, os.path.basename(path)[:-4] + '.shp')

        #     buffer_zone.to_file(filename)

    return print('Completed routing buffer zones')


def fit_edges(input_path, output_path):
    """
    Fit edges to nodes using a minimum spanning tree.

    Parameters
    ----------
    path : string
        Path to nodes shapefile.

    """
    folder = os.path.dirname(output_path)
    if not os.path.exists(folder):
        os.makedirs(folder)

    nodes = gpd.read_file(input_path, crs='epsg:4326')
    nodes = nodes.to_crs('epsg:3857')

    all_possible_edges = []

    for node1_id, node1 in nodes.iterrows():
        for node2_id, node2 in nodes.iterrows():
            if node1_id != node2_id:
                geom1 = shape(node1['geometry'])
                geom2 = shape(node2['geometry'])
                line = LineString([geom1, geom2])
                all_possible_edges.append({
                    'type': 'Feature',
                    'geometry': mapping(line),
                    'properties':{
                        # 'network_layer': 'core',
                        'from': node1_id,
                        'to':  node2_id,
                        'length': line.length,
                        # 'source': 'new',
                    }
                })
    if len(all_possible_edges) == 0:
        return

    G = nx.Graph()

    for node_id, node in enumerate(nodes):
        G.add_node(node_id, object=node)

    for edge in all_possible_edges:
        G.add_edge(edge['properties']['from'], edge['properties']['to'],
            object=edge, weight=edge['properties']['length'])

    tree = nx.minimum_spanning_edges(G)

    edges = []

    for branch in tree:
        link = branch[2]['object']
        if link['properties']['length'] > 0:
            edges.append(link)

    edges = gpd.GeoDataFrame.from_features(edges, crs='epsg:3857')

    if len(edges) > 0:
        edges = edges.to_crs('epsg:4326')
        edges.to_file(output_path)

    return print('Completed edge fitting')


def load_settlement_routing_lookup(path):
    """
    Load settlement routing lookup.

    """
    settlement_routing_lut = pd.read_csv(path, converters={'regions': eval})

    settlement_routing_lut = settlement_routing_lut.to_dict('records')

    output = []

    for item in settlement_routing_lut:
        for key, value in item.items():
            output.append(value)

    return output


def get_regions_to_model(region_id, GID_level, regions, settlement_routing_lookup):
    """
    Return the regions to model as a geopandas dataframe.

    """
    region_ids_to_model = settlement_routing_lookup.get(region_id)

    if region_ids_to_model:

        regions_to_model = regions[regions[GID_level].isin(region_ids_to_model)]

        return regions_to_model

    else:
        return []


def create_raster_tile_lookup(country):
    """
    Load the extents of each raster tile and place in lookup table.

    """
    iso3 = country['iso3']

    folder = os.path.join(DATA_RAW, 'gmted')
    paths = glob.glob(os.path.join(folder, '*.tif'))#[:1]

    output = []

    for path in paths:
        with rasterio.open(path) as src:
            bbox = src.bounds
            output.append({
                'x1': bbox[0],
                'y1': bbox[1],
                'x2': bbox[2],
                'y2': bbox[3],
                'path': path
            })

    output = pd.DataFrame(output)
    output.to_csv(os.path.join(DATA_INTERMEDIATE, iso3, 'raster_lookup.csv'), index=False)

    return print('Completed raster tile lookup')


if __name__ == '__main__':

    # countries = find_country_list(['Africa'])

    countries = [
        {'iso3': 'PER', 'iso2': 'PE', 'regional_level': 2, #'regional_nodes_level': 3,
            'region': 'SSA', 'pop_density_km2': 100, 'settlement_size': 100,
            'subs_growth': 3.5, 'smartphone_growth': 5, 'cluster': 'C1', 'coverage_4G': 16
        },
    ]

    for country in countries:

        print('Working on {}'.format(country['iso3']))

        # print('Processing country boundary ready to export')
        # process_country_shapes(country)

        # print('Processing regions ready to export')
        # process_regions(country)

        # print('Processing country population raster ready to export')
        # process_settlement_layer(country)

        # print('Generating the settlement layer ready to export')
        # generate_settlement_lut(country)

        # print('Find largest settlement in each region ready to export')
        # find_largest_regional_settlement(country)

        # print('Get settlement routing paths')
        # get_settlement_routing_paths(country)

        # print('Get settlement routing lookup')
        # get_settlement_routing_lookup(country)

        # print('Create regions to model')
        # create_regions_to_model(country)

        # print('Create routing buffer zone')
        # create_routing_buffer_zone(country)

        print('Generate raster tile lookup')
        create_raster_tile_lookup(country)

    print('Preprocessing complete')
