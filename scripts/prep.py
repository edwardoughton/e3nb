"""
Prepare all necessary data layers required for running the main
model script (scripts/run.py).

Written by Ed Oughton.

November 2020

"""
import os
import configparser
import json
import math
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
import pyproj
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, shape, mapping, box
from shapely.ops import unary_union, nearest_points, transform
import rasterio
import networkx as nx
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.mask import mask
from rasterstats import zonal_stats, gen_zonal_stats
import rioxarray as rxr
import xarray

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


def process_country_shapes(country):
    """
    Creates a single national boundary for the desired country.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    """
    iso3 = country['iso3']

    path = os.path.join(DATA_INTERMEDIATE, iso3)

    # if os.path.exists(os.path.join(path, 'national_outline.shp')):
    #     return 'Already completed national outline processing'

    if not os.path.exists(path):
        #Creating new directory
        os.makedirs(path)

    shape_path = os.path.join(path, 'national_outline.shp')

    #Loading all country shapes
    path = os.path.join(DATA_RAW, 'gadm36_levels_shp', 'gadm36_0.shp')
    countries = gpd.read_file(path)

    #Getting specific country shape
    single_country = countries[countries.GID_0 == iso3].reset_index()

    #Excluding small shapes
    single_country['geometry'] = single_country.apply(
        exclude_small_shapes, axis=1)

    #Adding ISO country code and other global information
    glob_info_path = os.path.join(DATA_RAW, 'global_information.csv')
    load_glob_info = pd.read_csv(glob_info_path, encoding = "ISO-8859-1")
    single_country = single_country.merge(
        load_glob_info,left_on='GID_0', right_on='ISO_3digit')

    if iso3 == 'IDN': #Indonesia is so large, we just want Sumatra
        single_country = subset(single_country)

    #Exporting processed country shape
    single_country.to_file(shape_path, driver='ESRI Shapefile')

    return


def subset(single_country):
    """
    Subset just Sumatra from Indonesia.

    """
    multi_geoms = list(single_country['geometry']).copy()

    areas = set()

    for geom in multi_geoms: #gets area of all shapes
        for item in list(geom):
            areas.add(item.area)

    areas = list(areas)
    areas.sort(reverse=True)

    output = []
    interim = []

    for geom in multi_geoms:
        for item in list(geom):
            if item.area == areas[0]: #get Sumatra and return as geopandas df
                interim.append(item)
            if item.area == areas[2]: #get Sumatra and return as geopandas df
                interim.append(item)

    output.append({
        'type': 'Feature',
        'geometry': MultiPolygon(interim),
        'properties': {}
    })

    output =  gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

    return output


def process_regions(country):
    """
    Function for processing the lowest desired subnational regions for the
    chosen country.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    """
    iso3 = country['iso3']
    level = country['lowest_regional_level']

    regions = []

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'regions')

    if not os.path.exists(folder):
        os.mkdir(folder)

    path = os.path.join(folder, '..', 'national_outline.shp')
    national_outline = gpd.read_file(path, crs='epsg:4328')
    national_outline = national_outline[['geometry']]

    for regional_level in range(1, level + 1):

        filename = 'regions_{}_{}.shp'.format(regional_level, iso3)

        path_processed = os.path.join(folder, filename)

        # if os.path.exists(path_processed):
        #     continue

        print('--Working on {}'.format(filename))

        filename = 'gadm36_{}.shp'.format(regional_level)
        path_regions = os.path.join(DATA_RAW, 'gadm36_levels_shp', filename)
        regions = gpd.read_file(path_regions)

        #Subsetting regions
        regions = regions[regions.GID_0 == iso3]

        regions = gpd.overlay(regions, national_outline, how='intersection')

        try:
            #Writing global_regions.shp to file
            regions.to_file(path_processed, driver='ESRI Shapefile')
        except:
            print('Unable to write {}'.format(filename))
            pass

    return


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

    # if os.path.exists(shape_path):
    #     return print('Completed settlement layer processing')

    # bbox = country.envelope
    geo = gpd.GeoDataFrame()
    geo = gpd.GeoDataFrame({'geometry': country['geometry']})
    coords = [json.loads(geo.to_json())['features'][0]['geometry']]

    #chop on coords
    out_img, out_transform = mask(settlements, coords, crop=True)

    # Copy the metadata
    out_meta = settlements.meta.copy()

    out_meta.update({"driver": "GTiff",
                    "height": out_img.shape[1],
                    "width": out_img.shape[2],
                    "transform": out_transform,
                    # "crs": 'epsg:4326'
                    })

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
            threshold = 0.05
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
    Generate a lookup table of all settlements over the defined
    settlement thresholds for the country being modeled.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)
    main_settlement_size = country['main_settlement_size']

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements')
    if not os.path.exists(folder):
        os.makedirs(folder)
    path_output = os.path.join(folder, 'settlements.shp')

    # if os.path.exists(path_output):
    #     return print('Already processed settlement lookup table (lut)')

    filename = 'regions_{}_{}.shp'.format(regional_level, iso3)
    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path, crs="epsg:4326")#[:20]
    regions = regions.loc[regions.is_valid]

    path_settlements = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements.tif')
    settlements = rasterio.open(path_settlements, 'r+')
    settlements.nodata = 0
    settlements.crs = {"init": "epsg:4326"}

    folder_tifs = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements', 'tifs')
    if not os.path.exists(folder_tifs):
        os.makedirs(folder_tifs)

    for idx, region in regions.iterrows():

        path_output = os.path.join(folder_tifs, region[GID_level] + '.tif')

        # if os.path.exists(path_output):
        #     continue

        bbox = region['geometry'].envelope

        geo = gpd.GeoDataFrame()
        geo = gpd.GeoDataFrame({'geometry': bbox}, index=[idx], crs='epsg:4326')
        coords = [json.loads(geo.to_json())['features'][0]['geometry']]

        #chop on coords
        out_img, out_transform = mask(settlements, coords, crop=True)

        # Copy the metadata
        out_meta = settlements.meta.copy()

        out_meta.update({"driver": "GTiff",
                        "height": out_img.shape[1],
                        "width": out_img.shape[2],
                        "transform": out_transform,
                        # "crs": 'epsg:4326'
                        })

        with rasterio.open(path_output, "w", **out_meta) as dest:
                dest.write(out_img)

    nodes = find_nodes(country, regions)

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
    main_nodes = settlements.loc[settlements['population'] >= main_settlement_size]
    main_nodes.to_file(path_output)

    settlements = settlements[['lon', 'lat', GID_level, 'population', 'type']]
    settlements.to_csv(os.path.join(folder, 'settlements.csv'), index=False)

    return


def find_nodes(country, regions):
    """
    Find key nodes in each region.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.
    regions : dataframe
        Pandas df containing all regions for modeling.

    Returns
    -------
    interim : list of dicts

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    threshold = country['pop_density_km2']
    settlement_size = country['settlement_size']

    folder_tifs = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements', 'tifs')

    interim = []

    # print('Working on gathering data from regional rasters')
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
                    for poly, value in polygons if value > 0]#, crs='epsg:4326'
            )

        if len(shapes_df) == 0: #if you put the crs in the preceeding function
            continue            #there is an error for an empty df
        shapes_df = shapes_df.set_crs('epsg:4326')

        geojson_region = [
            {'geometry': region['geometry'],
            'properties': {GID_level: region[GID_level]}
            }]

        gpd_region = gpd.GeoDataFrame.from_features(
                [{'geometry': poly['geometry'],
                    'properties':{GID_level: poly['properties'][GID_level]}}
                    for poly in geojson_region
                ]#, crs='epsg:4326'
            )

        if len(gpd_region) == 0: #if you put the crs in the preceeding function
            continue             #there is an error for an empty df
        gpd_region = gpd_region.set_crs('epsg:4326')

        nodes = gpd.overlay(shapes_df, gpd_region, how='intersection')

        results = []

        for idx, node in nodes.iterrows():
            pop = zonal_stats(
                node['geometry'],
                path,
                nodata=0,
                stats=['sum']
            )
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
            ]#, crs='epsg:4326'
        )

        nodes = nodes.drop_duplicates()

        if len(nodes) == 0: #if you put the crs in the preceeding function
            continue        #there is an error for an empty df
        nodes = nodes.set_crs('epsg:4326')

        nodes.loc[(nodes['sum'] >= 20000), 'type'] = '>20k'
        nodes.loc[(nodes['sum'] <= 10000) | (nodes['sum'] < 20000), 'type'] = '10-20k'
        nodes.loc[(nodes['sum'] <= 5000) | (nodes['sum'] < 10000), 'type'] = '5-10k'
        nodes.loc[(nodes['sum'] <= 1000) | (nodes['sum'] < 5000), 'type'] = '1-5k'
        nodes.loc[(nodes['sum'] <= 500) | (nodes['sum'] < 1000), 'type'] = '0.5-1k'
        nodes.loc[(nodes['sum'] <= 250) | (nodes['sum'] < 500), 'type'] = '0.25-0.5k'
        nodes.loc[(nodes['sum'] <= 250), 'type'] = '<0.25k'

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


def generate_agglomeration_lut(country):
    """
    Generate a lookup table of agglomerations.
    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    core_node_level = 'GID_{}'.format(country['core_node_level'])
    regional_node_level = 'GID_{}'.format(country['regional_node_level'])

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'agglomerations')
    if not os.path.exists(folder):
        os.makedirs(folder)
    path_output = os.path.join(folder, 'agglomerations.shp')

    if os.path.exists(path_output):
        return print('Agglomeration processing has already completed')

    print('Working on {} agglomeration lookup table'.format(iso3))

    filename = 'regions_{}_{}.shp'.format(regional_level, iso3)
    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path, crs="epsg:4326")#[:1]

    path_settlements = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements.tif')
    settlements = rasterio.open(path_settlements, 'r+')
    settlements.nodata = 255
    settlements.crs = {"init": "epsg:4326"}

    folder_tifs = os.path.join(DATA_INTERMEDIATE, iso3, 'agglomerations', 'tifs')
    if not os.path.exists(folder_tifs):
        os.makedirs(folder_tifs)

    for idx, region in regions.iterrows():

        path_output = os.path.join(folder_tifs, region[GID_level] + '.tif')

        if os.path.exists(path_output):
            continue

        # geo = gpd.GeoDataFrame({'geometry': region['geometry']}, index=[idx])
        geo = gpd.GeoDataFrame(geometry=gpd.GeoSeries(region['geometry']))

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

        with rasterio.open(path_output, "w", **out_meta) as dest:
                dest.write(out_img)

    print('Completed settlement.tif regional segmentation')

    nodes, missing_nodes = find_settlement_nodes(country, regions)

    nodes = gpd.GeoDataFrame.from_features(nodes, crs='epsg:4326')

    bool_list = nodes.intersects(regions['geometry'].unary_union)
    nodes = pd.concat([nodes, bool_list], axis=1)
    nodes = nodes[nodes[0] == True].drop(columns=0)

    agglomerations = []

    print('Identifying agglomerations')
    for idx1, region in regions.iterrows():
        seen_coords = set()
        for idx2, node in nodes.iterrows():
            if node['geometry'].intersects(region['geometry']):

                x = float(str(node['geometry'].x)[:12])
                y = float(str(node['geometry'].y)[:12])
                coord = '{}_{}'.format(x ,y)

                if coord in seen_coords:
                    continue #avoid duplicates

                agglomerations.append({
                    'type': 'Feature',
                    'geometry': mapping(node['geometry']),
                    'properties': {
                        'id': idx1,
                        'GID_0': region['GID_0'],
                        GID_level: region[GID_level],
                        core_node_level: region[core_node_level],
                        regional_node_level: region[regional_node_level],
                        'population': node['sum'],
                    }
                })
                seen_coords.add(coord)

        # if no settlements above the threshold values
        # find the most populated 1km2 cell centroid
        if len(seen_coords) == 0:

            pop_tif = os.path.join(folder_tifs, region[GID_level] + '.tif')

            with rasterio.open(pop_tif) as src:
                data = src.read()
                polygons = rasterio.features.shapes(data, transform=src.transform)
                shapes_df = gpd.GeoDataFrame.from_features(
                    [
                        {'geometry': poly, 'properties':{'value':value}}
                        for poly, value in polygons
                    ],
                    crs='epsg:4326'
                )
                shapes_df =shapes_df.nlargest(1, columns=['value'])

                shapes_df['geometry'] = shapes_df['geometry'].to_crs('epsg:3857')
                shapes_df['geometry'] = shapes_df['geometry'].centroid
                shapes_df['geometry'] = shapes_df['geometry'].to_crs('epsg:4326')
                geom = shapes_df['geometry'].values[0]

                x = float(str(node['geometry'].x)[:12])
                y = float(str(node['geometry'].y)[:12])
                coord = '{}_{}'.format(x ,y)

                if coord in seen_coords:
                    continue #avoid duplicates

                agglomerations.append({
                        'type': 'Feature',
                        'geometry': mapping(geom),
                        'properties': {
                            'id': 'regional_node',
                            'GID_0': region['GID_0'],
                            GID_level: region[GID_level],
                            core_node_level: region[core_node_level],
                            regional_node_level: region[regional_node_level],
                            'population': shapes_df['value'].values[0],
                        }
                    })

    agglomerations = gpd.GeoDataFrame.from_features(
            [
                {
                    'geometry': item['geometry'],
                    'properties': {
                        'id': item['properties']['id'],
                        'GID_0':item['properties']['GID_0'],
                        GID_level: item['properties'][GID_level],
                        core_node_level: item['properties'][core_node_level],
                        regional_node_level: item['properties'][regional_node_level],
                        'population': item['properties']['population'],
                    }
                }
                for item in agglomerations
            ],
            crs='epsg:4326'
        )

    agglomerations = agglomerations.drop_duplicates(subset=['geometry']).reset_index()

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'agglomerations')
    path_output = os.path.join(folder, 'agglomerations' + '.shp')

    agglomerations.to_file(path_output)

    agglomerations['lon'] = agglomerations['geometry'].x
    agglomerations['lat'] = agglomerations['geometry'].y
    agglomerations = agglomerations[['lon', 'lat', GID_level, 'population']]
    agglomerations = agglomerations.drop_duplicates(subset=['lon', 'lat']).reset_index()
    agglomerations.to_csv(os.path.join(folder, 'agglomerations.csv'), index=False)

    return print('Agglomerations layer complete')


def find_settlement_nodes(country, regions):
    """
    Find key nodes.
    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    core_node_level = 'GID_{}'.format(country['core_node_level'])
    regional_node_level = 'GID_{}'.format(country['regional_node_level'])

    threshold = country['pop_density_km2']
    settlement_size = country['settlement_size']

    folder_tifs = os.path.join(DATA_INTERMEDIATE, iso3, 'agglomerations', 'tifs')

    interim = []
    missing_nodes = set()

    print('Working on gathering data from regional rasters')
    for idx, region in regions.iterrows():

        path = os.path.join(folder_tifs, region[GID_level] + '.tif')

        with rasterio.open(path) as src:
            data = src.read()
            data[data < threshold] = 0
            data[data >= threshold] = 1
            polygons = rasterio.features.shapes(data, transform=src.transform)
            shapes_df = gpd.GeoDataFrame.from_features(
                [
                    {'geometry': poly, 'properties':{'value':value}}
                    for poly, value in polygons
                    if value > 0
                ]
            )
        if len(shapes_df) == 0:
            continue

        shapes_df = shapes_df.set_crs('epsg:4326')

        geojson_region = [
            {
                'geometry': region['geometry'],
                'properties': {
                    GID_level: region[GID_level],
                    core_node_level: region[core_node_level],
                    regional_node_level: region[regional_node_level],
                }
            }
        ]

        gpd_region = gpd.GeoDataFrame.from_features(
                [
                    {'geometry': poly['geometry'],
                    'properties':{
                        GID_level: poly['properties'][GID_level],
                        core_node_level: region[core_node_level],
                        regional_node_level: region[regional_node_level],
                        }}
                    for poly in geojson_region
                ], crs='epsg:4326'
            )

        if len(shapes_df) == 0:
            continue

        nodes = gpd.overlay(shapes_df, gpd_region, how='intersection')

        stats = zonal_stats(shapes_df['geometry'], path, stats=['count', 'sum'])

        stats_df = pd.DataFrame(stats)

        nodes = pd.concat([shapes_df, stats_df], axis=1).drop(columns='value')

        nodes_subset = nodes[nodes['sum'] >= settlement_size]

        if len(nodes_subset) == 0:
            missing_nodes.add(region[GID_level])

        for idx, item in nodes_subset.iterrows():
            interim.append({
                    'geometry': item['geometry'].centroid,
                    'properties': {
                        GID_level: region[GID_level],
                        core_node_level: region[core_node_level],
                        regional_node_level: region[regional_node_level],
                        'count': item['count'],
                        'sum': item['sum']
                    }
            })

    return interim, missing_nodes


def find_largest_regional_settlement(country):
    """
    Find the largest settlement in each region as the main regional
    routing node.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
    path_output = os.path.join(folder, 'largest_regional_settlements.shp')

    # if os.path.exists(path_output):
    #     return print('Already processed the largest regional settlement layer')

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements')
    path_input = os.path.join(folder, 'settlements' + '.shp')
    nodes = gpd.read_file(path_input, crs='epsg:4326')

    nodes = nodes.loc[nodes.reset_index().groupby([GID_level])['population'].idxmax()]
    nodes.to_file(path_output, crs='epsg:4326')

    return


def get_settlement_routing_paths(country):
    """
    Create settlement routing paths and export as linestrings.

    This is based on the largest regional settlement being routed
    to the nearest major settlement, which may or may not be within
    its own region. Any settlements routing to a major settlement from
    a different region will later be combined into a single region
    for modeling purposes.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)
    main_settlement_size = country['main_settlement_size']

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
    path_output = os.path.join(folder, 'settlement_routing.shp')

    # if os.path.exists(path_output):
    #     return print('Already processed the settlement routing path layer')

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
    path_input = os.path.join(folder, 'largest_regional_settlements.shp')
    regional_nodes = gpd.read_file(path_input, crs='epsg:4326')

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
    path_input = os.path.join(folder, 'main_nodes.shp')
    main_nodes = gpd.read_file(path_input, crs='epsg:4326')

    paths = []

    for idx, regional_node in regional_nodes.iterrows():

        if regional_node['population'] > main_settlement_size:
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

    #if you don't flip to projected you get an error here
    #even though the buffer isn't being used to explicitely measure distance
    paths['geometry'] = paths['geometry'].to_crs('epsg:3857').buffer(0.01)

    paths['geometry'] = paths['geometry'].to_crs('epsg:4326')

    geoms = paths.geometry.unary_union
    paths = gpd.GeoDataFrame(geometry=[geoms])

    paths = paths.explode().reset_index(drop=True)

    paths.to_file(path_output, crs='epsg:4326')

    return


def create_regions_to_model(country):
    """
    Any settlements routing to a major settlement from a different
    region are combined into a single region for modeling purposes.

    To combine multiple regions, a union is formed. This is achieved
    by intersecting regions with the settlement routing linestrings.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    """
    iso3 = country['iso3']
    GID_level = 'GID_{}'.format(country['regional_level'])

    filename = 'regions_{}_{}.shp'.format(country['regional_level'], iso3)
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'regions', filename)
    regions = gpd.read_file(path, crs='epsg:4326')
    regions = regions.drop_duplicates()#[:1]
    regions = regions.loc[regions.is_valid]

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

        unique_list = regions_to_model[GID_level].unique()
        unique_names = regions_to_model['NAME_1'].unique()

        unique_regions = str(unique_list).replace('[', '').replace(']', '').replace(' ', '-')
        unique_names = str(unique_names).replace('[', '').replace(']', '').replace(' ', '-')

        regions_to_model = regions_to_model.copy()
        regions_to_model['modeled_regions'] = unique_regions
        regions_to_model['unique_names'] = unique_names
        regions_to_model = regions_to_model.dissolve(by=['modeled_regions'])#, 'unique_names'

        output.append({
            'geometry': regions_to_model['geometry'][0],
            'properties': {
                'regions': unique_regions,
                'names': unique_names,
            }
        })

        for item in unique_list:
            seen.add(item)

    for idx, region in regions.iterrows():

        # if region[GID_level] == 'PER.8.9_1':
        #     print(region)

        if not region[GID_level] in list(seen):

            output.append({
                'geometry': region['geometry'],
                'properties': {
                    'regions': region[GID_level],
                    'names': region['NAME_1'],
                }
            })

            seen.add(region[GID_level])

    output = gpd.GeoDataFrame.from_features(output)
    filename = 'modeling_regions.shp'
    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'modeling_regions')

    if not os.path.exists(folder):
        os.makedirs(folder)

    output.to_file(os.path.join(folder, filename), crs='epsg:4326')

    return


def create_routing_buffer_zone(country):
    """
    A routing buffer is required to reduce the size of the problem.

    In the model run script, the routing buffer is use to search
    for potential sites.

    To create the routing zone, a minimum spanning tree is fitted
    between the desired settlements, with a buffer and union consequently
    being added.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

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
    modeling_regions = gpd.read_file(path, crs='epsg:4326')#[:1]

    for idx, region in modeling_regions.iterrows():

        modeling_region = gpd.GeoDataFrame.from_features([{
            'geometry': mapping(region['geometry']),
            'properties': {
                'regions': region['regions']
            }
        }], crs='epsg:4326')

        nodes = gpd.overlay(settlements, modeling_region, how='intersection')

        main_node = (nodes[nodes['population'] == nodes['population'].max()])

        if not len(main_node) > 0:
            continue

        #export nodes
        path_nodes = os.path.join(folder_nodes, main_node.iloc[0][GID_level] + '.shp')
        nodes.to_file(path_nodes, crs='epsg:4326')

        #export edges
        path_edges = os.path.join(folder_edges, main_node.iloc[0][GID_level] + '.shp')
        fit_edges(path_nodes, path_edges, modeling_region)

        #export individual modeling region shape
        folder_regions = os.path.join(DATA_INTERMEDIATE, iso3, 'modeling_regions')
        path = os.path.join(folder_regions, main_node.iloc[0][GID_level] + '.shp')
        modeling_region.to_file(path, crs='epsg:4326')

    return


def fit_edges(input_path, output_path, modeling_region):
    """
    Fit edges to nodes using a minimum spanning tree.

    Parameters
    ----------
    input_path : string
        Path to the node shapefiles.
    output_path : string
        Path for writing the network edge shapefiles.
    modeling_region : geojson
        The modeling region being assessed.

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
                        # 'from_population': node1['population'],
                        # 'from_type': node1['type'],
                        # 'from_lon': node1['lon'],
                        # 'from_lat': node1['lat'],
                        'to':  node2_id,
                        # 'to_population': node2['population'],
                        # 'to_type': node2['type'],
                        # 'to_lon': node2['lon'],
                        # 'to_lat': node2['lat'],
                        'length': line.length,
                        # 'source': 'new',
                        'regions': modeling_region['regions'].iloc()[0],
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

    return


def create_raster_tile_lookup(country):
    """
    Load the extents of each raster tile and place in lookup table.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    """
    iso3 = country['iso3']

    path = os.path.join(DATA_INTERMEDIATE, iso3, 'national_outline.shp')
    outline = gpd.read_file(path, crs='epsg:4326')
    outline = outline['geometry'].envelope

    folder = os.path.join(DATA_RAW, 'gmted')
    paths = glob.glob(os.path.join(folder, '*.tif'))#[:1]

    output = []

    for path in paths:
        with rasterio.open(path) as src:
            bbox = src.bounds

            bbox_shape = box(bbox[0], bbox[1], bbox[2], bbox[3])

            if bbox_shape.intersects(outline[0]):
                output.append({
                    'x1': bbox[0],
                    'y1': bbox[1],
                    'x2': bbox[2],
                    'y2': bbox[3],
                    'path': path
                })

    output = pd.DataFrame(output)
    output.to_csv(os.path.join(DATA_INTERMEDIATE, iso3, 'raster_lookup.csv'), index=False)

    return


def process_canopy_height_data(country):
    """
    Load in canopy height data and subset by country.

    """
    iso3 = country['iso3']

    directory = os.path.join(DATA_INTERMEDIATE, iso3, 'canopy_heights')

    if not os.path.exists(directory):
        os.makedirs(directory)

    path_processed = os.path.join(directory, 'canopy_heights.shp')

    path_heights = os.path.join(
        DATA_RAW,
        'LIDAR_FOREST_CANOPY_HEIGHTS_1271',
        'data',
        'All_countries_hmax_hlorey.shp'
    )

    height_data = gpd.read_file(path_heights, crs='epsg:4326')

    height_data = height_data.loc[height_data['Country'] == country['name']]

    height_data.to_file(path_processed, driver='ESRI Shapefile')

    return



# def process_canopy_height_data(country):
#     """
#     Load in canopy height data and subset by country.

#     """

    # path = os.path.join(DATA_INTERMEDIATE, iso3, 'national_outline.shp')
    # outline = gpd.read_file(path, crs='epsg:4326')
    # outline = outline['geometry'].envelope

    # output = []

    # for idx, height_point in height_data.iterrows():
    #     if height_point['geometry'].intersects(outline[0]):





    # height_data = gpd.overlay(height_data, outline, how='intersection')
    # print(height_data)
    # try:
    #     print(path_processed)
    #     #Writing global_regions.shp to file

    # except:
    #     print('Unable to write canopy_heights for {}'.format(iso3))
    #     pass


    # output = pd.DataFrame(output)
    # directory = os.path.join(DATA_INTERMEDIATE, iso3, 'modis_lookup.csv')
    # output.to_csv(directory, index=False)


def create_pop_and_terrain_regional_lookup(country):
    """
    Extract regional luminosity and population data.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    """
    iso3 = country['iso3']

    path_settlements = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements.tif')

    filename = 'modeling_regions.shp'
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'modeling_regions', filename)
    modeling_regions = gpd.read_file(path, crs='epsg:4326')#[:10]

    filename = 'main_nodes.shp'
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure', filename)
    main_nodes = gpd.read_file(path, crs='epsg:4326')#[:5]

    filename = 'canopy_heights.shp'
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'canopy_heights', filename)
    height_data = gpd.read_file(path, crs='epsg:4326')#[:5]

    tile_lookup = load_raster_tile_lookup(country)

    output = []

    for index, modeling_region in modeling_regions.iterrows():

        # if not modeling_region['regions'] == 'PER.15.1_1':
        #     continue

        area_km2 = get_area(modeling_region)

        path_input = find_correct_raster_tile(modeling_region['geometry'].bounds,
            tile_lookup)

        stats = next(gen_zonal_stats(
            modeling_region['geometry'],
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
                modeling_region['geometry'],
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

        if modeling_region['geometry'].type == 'Polygon':
            region_geom = gpd.GeoDataFrame({'geometry': modeling_region['geometry']},
                index=[0], crs='epsg:4326')
        else:
            region_geom = gpd.GeoDataFrame({'geometry': modeling_region['geometry']},
                crs='epsg:4326')

        main_node = gpd.overlay(main_nodes, region_geom, how='intersection')
        if len(main_node) == 0:
            continue
        modeling_region_id = main_node['GID_{}'.format(country['regional_level'])].values[0]

        m_region = gpd.GeoDataFrame(gpd.GeoSeries(modeling_region['geometry']))
        m_region = m_region.rename(columns={0:'geometry'}).set_geometry('geometry')
        m_region = m_region.set_crs('epsg:4326')
        canopy_height = gpd.overlay(height_data, m_region, how='intersection')

        if len(canopy_height) > 0:
            max_canopy_height = canopy_height['new_hmax'].max()
            mean_canopy_height = canopy_height['new_hmax'].mean()
        else:
            max_canopy_height = 'no data'
            mean_canopy_height = 'no data'

        output.append({
            'modeling_region': modeling_region_id,
            'regions': modeling_region['regions'],
            'names': modeling_region['names'],
            'id_range_m': id_range_m,
            'population': population,
            'area_km2': area_km2,
            'pop_density_km2': pop_density_km2,
            'max_canopy_height': max_canopy_height,
            'mean_canopy_height': mean_canopy_height,
        })

    output = pd.DataFrame(output)

    filename = 'population_and_terrain_lookup.csv'
    path = os.path.join(DATA_INTERMEDIATE, iso3, filename)
    output.to_csv(path, index=False)

    return print('Completed population and terrain lookup')


def get_area(modeling_region):
    """
    Return the area in square km.

    Parameters
    ----------
    modeling_region : series
        The modeling region that we wish to find the area for.

    """
    project = pyproj.Transformer.from_crs('epsg:4326', 'esri:54009', always_xy=True).transform
    new_geom = transform(project, modeling_region['geometry'])
    area_km2 = new_geom.area / 1e6

    return area_km2


def load_raster_tile_lookup(country):
    """
    Load in the preprocessed raster tile lookup.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    Returns
    -------
    lookup : dict
        A lookup table containing raster tile boundary coordinates
        as the keys, and the file paths as the values.

    """
    iso3 = country['iso3']

    path = os.path.join(DATA_INTERMEDIATE, iso3, 'raster_lookup.csv')
    data = pd.read_csv(path)
    data = data.to_records('dicts')

    lookup = {}

    for item in data:

        coords = (item['x1'], item['y1'], item['x2'], item['y2'])

        lookup[coords] = item['path']

    return lookup


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


def process_modis(country):
    """
    Process the modis data by converting from .hdf to .tif.

    """
    path = os.path.join(DATA_RAW, 'modis', '.hdf')
    all_paths = glob.glob(path + '/*.hdf')#[:1]

    for path in all_paths:

        filename_out = os.path.basename(path)[:-4] + ".tif"
        directory = os.path.join(DATA_RAW, 'modis', '.tif')
        path_out = os.path.join(directory, filename_out)

        if not os.path.exists(os.path.dirname(path_out)):
            os.makedirs(os.path.dirname(path_out))

        if not os.path.exists(path_out):

            print('Working on : {}'.format(path))

            modis_pre = rxr.open_rasterio(path, masked=True)

            modis_pre = modis_pre.rio.reproject("EPSG:4326")

            modis_pre.Percent_Tree_Cover.rio.to_raster(path_out, crs='epsg:4326')

    return


def create_modis_tile_lookup(country):
    """
    Load the extents of each modis raster tile and place in lookup table.

    Parameters
    ----------
    country : dict
        Contains all country-specific information for modeling.

    """
    iso3 = country['iso3']

    path = os.path.join(DATA_INTERMEDIATE, iso3, 'national_outline.shp')
    outline = gpd.read_file(path, crs='epsg:4326')
    outline = outline['geometry'].envelope

    folder = os.path.join(DATA_RAW, 'modis', '.tif')
    paths = glob.glob(os.path.join(folder, '*.tif'))#[:1]

    output = []

    for path in paths:
        with rasterio.open(path) as src:

            bbox = src.bounds

            bbox_shape = box(bbox[0], bbox[1], bbox[2], bbox[3])

            if bbox_shape.intersects(outline[0]):
                output.append({
                    'x1': bbox[0],
                    'y1': bbox[1],
                    'x2': bbox[2],
                    'y2': bbox[3],
                    'path': path
                })

    output = pd.DataFrame(output)
    directory = os.path.join(DATA_INTERMEDIATE, iso3, 'modis_lookup.csv')
    output.to_csv(directory, index=False)

    return


if __name__ == '__main__':

    countries = [
        {
            'iso3': 'PER', 'iso2': 'PE', 'name': 'Peru',
            'regional_level': 2,
            'lowest_regional_level': 3, 'region': 'LAT',
            'pop_density_km2': 50, 'settlement_size': 100,
            'main_settlement_size': 20000, 'subs_growth': 3.5,
            'smartphone_growth': 5, 'cluster': 'C1', 'coverage_4G': 16,
            'core_node_level': 1, 'regional_node_level': 2,
        },
        {
            'iso3': 'IDN', 'iso2': 'ID', 'name': 'Indonesia',
            'regional_level': 2,
            'lowest_regional_level': 3, 'region': 'SEA',
            'pop_density_km2': 50, 'settlement_size': 100,
            'main_settlement_size': 20000,  'subs_growth': 3.5,
            'smartphone_growth': 5, 'cluster': 'C1', 'coverage_4G': 16,
            'core_node_level': 2, 'regional_node_level': 2,
        },
    ]

    for country in countries:

        print('Working on {}'.format(country['iso3']))

        # ### Processing country boundary ready to export
        # process_country_shapes(country)

        # ### Processing regions ready to export
        # process_regions(country)

        # ### Processing country population raster ready to export
        # process_settlement_layer(country)

        # # ### Generating the settlement layer ready to export
        # generate_agglomeration_lut(country)

        # ### Find largest settlement in each region ready to export
        # find_largest_regional_settlement(country)

        # ### Get settlement routing paths
        # get_settlement_routing_paths(country)

        # # ### Create regions to model
        # create_regions_to_model(country)

        # ### Create routing buffer zone
        # create_routing_buffer_zone(country)

        # ### Generate raster tile lookup
        # create_raster_tile_lookup(country)

        # ## Process tree canopy height data
        # process_canopy_height_data(country)

        # Create population and terrain regional lookup
        create_pop_and_terrain_regional_lookup(country)

        # ## Process the modis data
        # process_modis(country)

        # ## Generate modis tile lookup
        # create_modis_tile_lookup(country)

    print('Preprocessing complete')
