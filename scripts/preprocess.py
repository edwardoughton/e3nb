"""
Process agglomeration layer

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

    # if os.path.exists(shape_path):
    #     return print('Completed settlement layer processing')

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


def generate_agglomeration_lut(country):
    """
    Generate a lookup table of agglomerations.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

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
    regions = gpd.read_file(path, crs="epsg:4326")

    path_settlements = os.path.join(DATA_INTERMEDIATE, iso3, 'settlements.tif')
    settlements = rasterio.open(path_settlements, 'r+')
    settlements.nodata = 255
    settlements.crs = {"init": "epsg:4326"}

    folder_tifs = os.path.join(DATA_INTERMEDIATE, iso3, 'agglomerations', 'tifs')
    if not os.path.exists(folder_tifs):
        os.makedirs(folder_tifs)

    for idx, region in regions.iterrows():

        # if not region['GID_2'] in single_region:
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

    nodes, missing_nodes = find_nodes(country, regions)

    if len(missing_nodes) > 0:
        nodes = nodes + missing_nodes

    nodes = gpd.GeoDataFrame.from_features(nodes, crs='epsg:4326')

    bool_list = nodes.intersects(regions['geometry'].unary_union)
    nodes = pd.concat([nodes, bool_list], axis=1)
    nodes = nodes[nodes[0] == True].drop(columns=0)

    agglomerations = []

    print('Identifying agglomerations')
    for idx1, region in regions.iterrows():

        # if not region['GID_2'] in single_region:
        #     continue

        seen = set()
        for idx2, node in nodes.iterrows():
            if node['geometry'].intersects(region['geometry']):
                if node['sum'] > 0:
                    agglomerations.append({
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

    agglomerations = gpd.GeoDataFrame.from_features(
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
                for item in agglomerations
            ],
            crs='epsg:4326'
        )

    agglomerations['lon'] = round(agglomerations['geometry'].x, 5)
    agglomerations['lat'] = round(agglomerations['geometry'].y, 5)

    agglomerations = agglomerations.drop_duplicates(subset=['lon', 'lat'])

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'agglomerations')
    path_output = os.path.join(folder, 'agglomerations' + '.shp')
    agglomerations.to_file(path_output)

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
    path_output = os.path.join(folder, 'main_nodes' + '.shp')
    main_nodes = agglomerations.loc[agglomerations['population'] >= 20000]
    main_nodes.to_file(path_output)

    agglomerations = agglomerations[['lon', 'lat', GID_level, 'population', 'type']]
    agglomerations.to_csv(os.path.join(folder, 'agglomerations.csv'), index=False)

    return print('Agglomerations layer complete')


def find_nodes(country, regions):
    """
    Find key nodes.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    threshold = country['pop_density_km2']
    settlement_size = country['settlement_size']

    folder_tifs = os.path.join(DATA_INTERMEDIATE, iso3, 'agglomerations', 'tifs')

    interim = []

    print('Working on gathering data from regional rasters')
    for idx, region in regions.iterrows():

        # if not region['GID_2'] in single_region:
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

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'agglomerations')
    path_input = os.path.join(folder, 'agglomerations' + '.shp')
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

    if os.path.exists(path_output):
        return print('Settlement routing paths already exist')

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

        paths.append({
            'type': 'LineString',
            'geometry': mapping(geom),
            'properties': {
                'id': idx,
                'source': regional_node[GID_level],
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

    paths.to_file(path_output, crs='epsg:4326')

    return print('Completed settlement routing paths ')


def get_settlement_routing_lookup(country):
    """
    Create settlement routing lookup.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']
    GID_level = 'GID_{}'.format(regional_level)

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
    path_output = os.path.join(folder, 'settlement_routing_lookup.csv')

    if os.path.exists(path_output):
        return print('Settlement routing lookup already exists')

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure')
    path_input = os.path.join(folder, 'settlement_routing.shp')
    paths = gpd.read_file(path_input, crs='epsg:4326')#[:1]

    folder = os.path.join(DATA_INTERMEDIATE, iso3, 'regions')
    path_input = os.path.join(folder, 'regions_{}_PER.shp'.format(regional_level))
    regions = gpd.read_file(path_input, crs='epsg:4326')

    seen = set()
    output = []

    for idx, path in paths.iterrows():

        seen.add(path['source'])
        region_intersections = []

        for idx, region in regions.iterrows():

            # if not path['source'] == 'PER.17.5_1':
            #     continue

            if path['geometry'].intersects(region['geometry']):

                region_intersections.append(region[GID_level])

        output.append({
            'id': path['id'],
            'source': path['source'],
            'regions': region_intersections
            })

    for idx, region in regions.iterrows():
        if not region[GID_level] in list(seen):
            output.append({
                'id': 'NA',
                'source': region[GID_level],
                'regions': [region[GID_level]],
                })

    output = pd.DataFrame(output)
    output.to_csv(path_output, index=False)

    return print('Completed settlement routing lookup')


def create_regions_to_model(country):
    """
    Subset areas to model. Create a union when multiple areas are required.

    """
    iso3 = country['iso3']
    GID_level = 'GID_{}'.format(country['regional_level'])

    filename = 'regions_{}_{}.shp'.format(country['regional_level'], iso3)
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'regions', filename)
    regions = gpd.read_file(path, crs='apsg:4326')

    filename = 'settlement_routing_lookup.csv'
    path = os.path.join(DATA_INTERMEDIATE, iso3, 'network_routing_structure', filename)
    settlement_routing_lookup = load_settlement_routing_lookup(path)

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
        unique_regions = unique_regions.replace('[', '').replace(']', '').replace(' ', '_')
        regions_to_model = regions_to_model.copy()
        regions_to_model['modeled_regions'] = unique_regions
        regions_to_model = regions_to_model.dissolve(by='modeled_regions')

        filename = '{}.shp'.format(unique_regions)
        folder = os.path.join(DATA_INTERMEDIATE, iso3, 'modeling_regions')
        path = os.path.join(folder, filename)

        if not os.path.exists(folder):
            os.makedirs(folder)

        regions_to_model.to_file(path, crs='epsg:4326')

        grid = generate_grid(regions_to_model, 10000, 10000)

        folder = os.path.join(DATA_INTERMEDIATE, iso3, 'grid')

        if not os.path.exists(folder):
            os.makedirs(folder)

        grid.to_file(os.path.join(folder, '{}.shp'.format(unique_regions)))

    return print('Completed creation of regions to model')


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


def load_settlement_routing_lookup(path):
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


def process_dem(country):
    """
    Clip the dem given a set of grid tiles.

    Parameters
    ----------
    country : string
        Three digit ISO country code.

    """
    iso3 = country['iso3']

    filename = '10S090W_20101117_gmted_med300.tif'
    path_dem = os.path.join(DATA_RAW, 'gmted', filename)

    path = os.path.join(DATA_INTERMEDIATE, iso3, 'grid')
    all_paths = glob.glob(path + '/*.shp')

    for path in all_paths:

        tiles = gpd.read_file(path)

        folder = os.path.join(DATA_INTERMEDIATE, iso3, 'gmted', os.path.basename(path)[:-4])

        if not os.path.exists(folder):
            os.makedirs(folder)

        for idx, grid_tile in tiles.iterrows():

            x = grid_tile['geometry'].centroid.x
            y = grid_tile['geometry'].centroid.y
            tile_centroid = '{}_{}'.format(x, y)

            grid_tile = gpd.GeoDataFrame({'geometry': grid_tile['geometry']}, index=[0])

            bbox = grid_tile.envelope

            geo = gpd.GeoDataFrame({'geometry': bbox}, crs=('epsg:4326'))

            coords = [json.loads(geo.to_json())['features'][0]['geometry']]

            dem = rasterio.open(path_dem, "r+")
            dem.nodata = 0

            out_img, out_transform = mask(dem, coords, crop=True)

            out_meta = dem.meta.copy()

            out_meta.update({"driver": "GTiff",
                            "height": out_img.shape[1],
                            "width": out_img.shape[2],
                            "transform": out_transform,
                            "crs": 'epsg:4326'})

            path_output = os.path.join(folder, '{}.tif'.format(tile_centroid))

            with rasterio.open(path_output, "w", **out_meta) as dest:
                    dest.write(out_img)

    return print('Completed processing of dem layer')


def create_high_points(country):
    """
    Gets the highest point in each tile.

    argmax and unravel index find the row and column of the max value in the raster matrix
    then src.xy transforms back to geographic coordinates (in whatever CRS the raster is in)

    """
    iso3 = country['iso3']

    paths = glob.glob(os.path.join(DATA_INTERMEDIATE, iso3, 'gmted' + '/*'))

    for path in paths:

        folder = os.path.join(DATA_INTERMEDIATE, iso3, 'high_points')

        if not os.path.exists(folder):
            os.makedirs(folder)

        all_paths = glob.glob(path + '\*')

        output = []

        for tile_path in all_paths:

            with rasterio.open(tile_path) as src:
                ds = src.read(1)
                row, col = np.unravel_index(np.argmax(ds, axis=None), ds.shape)
                maxval = ds[row, col]
                x, y = src.xy(row, col)
                output.append({
                    'geometry': {
                        'type': 'Point',
                        'coordinates': (x, y)
                    },
                    'properties': {
                        'row': row,
                        'col': col,
                        'height_m': maxval,
                        'modeling_region': os.path.basename(path),
                        'tile': os.path.basename(tile_path)[:-4]
                    }
                })

        output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

        filename = '{}.shp'.format(os.path.basename(path))
        output.to_file(os.path.join(folder, filename), crs='epsg:4326')

    return print('Completed creation of high points')


def reproject_raster():
    """
    Convert the raster layer to 3857.

    """
    filename = '10S090W_20101117_gmted_med300.tif'
    path_input = os.path.join(DATA_RAW, 'gmted', filename)
    path_output = os.path.join(DATA_RAW, 'gmted', '10S090W_20101117_gmted_med300_reprojected.tif')

    crs = {'init': 'epsg:3857'}

    # reproject raster to project crs
    with rasterio.open(path_input) as src:

        src_crs = src.crs

        transform, width, height = calculate_default_transform(
            src_crs, crs, src.width, src.height, *src.bounds)

        kwargs = src.meta.copy()

        kwargs.update({
            'crs': crs,
            'transform': transform,
            'width': width,
            'height': height})

        with rasterio.open(path_output, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=crs,
                    resampling=Resampling.nearest)

    return print('Completed raster reprojection')


def process_viewsheds(country):
    """
    Process viewsheds for all highpoints.

    """
    iso3 = country['iso3']

    filename = '10S090W_20101117_gmted_med300_reprojected.tif'
    path_input = os.path.join(DATA_RAW, 'gmted', filename)

    paths = glob.glob(os.path.join(DATA_INTERMEDIATE, iso3, 'high_points' + '/*.shp'))

    for path in paths:

        path_output = os.path.join(DATA_INTERMEDIATE, iso3, 'viewsheds', os.path.basename(path)[:-4])

        if not os.path.exists(path_output):
            os.makedirs(path_output)

        high_points = gpd.read_file(path, crs='epsg:4326')#[:2]
        high_points = high_points.to_crs('epsg:3857')

        for idx, point in high_points.iterrows():

            tile_name = point['tile']

            with Session(gisdb=path_output, location="location", create_opts="EPSG:3857"):

                print('parse command')
                print(gcore.parse_command("g.gisenv", flags="s"))#, set="DEBUG=3"

                print('r.external')
                # now link a GDAL supported raster file to a binary raster map layer,
                # from any GDAL supported raster map format, with an optional title.
                # The file is not imported but just registered as GRASS raster map.
                gcore.run_command('r.external', input=path_input, output=tile_name, overwrite=True)

                print('r.external.out')
                #write out as geotiff
                gcore.run_command('r.external.out', directory='viewsheds', format="GTiff")

                print('r.region')
                #manage the settings of the current geographic region
                gcore.run_command('g.region', raster=tile_name)

                print('r.viewshed')
                #for each point in the output that is NULL: No LOS
                gcore.run_command('r.viewshed',
                        input=tile_name,
                        output='{}.tif'.format(tile_name),
                        coordinate= [point['geometry'].x, point['geometry'].y], #[-8711068, -509143],#[27.5, -3.5],
                        observer_elevation=30,
                        target_elevation=30,
                        memory=5000,
                        overwrite=True,
                        quiet=True,
                        max_distance=40000,
                        # verbose=True
                )

    return print('Completed viewsheds')


def export_los_lookup(country):
    """
    Export a los lookup for each modeled area.

    """
    iso3 = country['iso3']
    radius = 40000

    path_output = os.path.join(DATA_INTERMEDIATE, iso3, 'los_lookup')

    if not os.path.exists(path_output):
        os.makedirs(path_output)

    paths = glob.glob(os.path.join(DATA_INTERMEDIATE, iso3, 'high_points' + '/*.shp'))

    for path in paths:

        high_points = gpd.read_file(path, crs='epsg:4326')#[:5]
        high_points = high_points.to_crs('epsg:3857')

        results = []

        for idx, point in high_points.iterrows():

            tile_name = point['tile']

            x_source = point['geometry'].centroid.x
            y_source = point['geometry'].centroid.y
            point_coords = '{}_{}'.format(x_source, y_source)

            point['geometry'] = point['geometry'].buffer(radius)

            within_radius = high_points[high_points.within(point['geometry'])]

            viewshed_path = os.path.join(DATA_INTERMEDIATE, iso3, 'viewsheds',
                os.path.basename(path)[:-4], 'location', 'PERMANENT', 'viewsheds', tile_name + '.tif')

            for idx, node in within_radius.iterrows():

                x_sink = node['geometry'].centroid.x
                y_sink = node['geometry'].centroid.y
                node_coords = '{}_{}'.format(x_sink, y_sink)

                if point_coords == node_coords:
                    continue

                distance = measure_distance(x_source, y_source, x_sink, y_sink)

                geo = gpd.GeoDataFrame({'geometry': [node['geometry']]}, index=[0])

                with rasterio.open(viewshed_path) as src:

                    out_image, out_transform = mask(src, geo['geometry'], crop=True)

                    value = out_image[0][0][0]

                    if not np.isnan(value):
                        results.append({
                            'type': 'los',
                            'source': point_coords,
                            'sink': node_coords,
                            'distance_m': distance,
                        })
                    else:
                        results.append({
                            'type': 'nlos',
                            'source': point_coords,
                            'sink': node_coords,
                            'distance_m': distance,
                        })

        results = pd.DataFrame(results)

        filename = os.path.basename(path)[:-4] + '.csv'
        results.to_csv(os.path.join(path_output, filename), index=False)


def measure_distance(x1, y1, x2, y2):
    """
    Find distance between two sets of points.

    """
    distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    return distance


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

        # print('Processing country boundary')
        # process_country_shapes(country)

        # print('Processing regions')
        # process_regions(country)

        # print('Processing settlement layer')
        # process_settlement_layer(country)

        # print('Generating agglomeration layer')
        # generate_agglomeration_lut(country)

        # print('Find largest settlement in each region')
        # find_largest_regional_settlement(country)

        # print('Get settlement routing paths')
        # get_settlement_routing_paths(country)

        # print('Get settlement routing lookup')
        # get_settlement_routing_lookup(country)

        # print('Create regions to model')
        # create_regions_to_model(country)

        # print('Processing dem')
        # process_dem(country)

        # print('Extract high points')
        # create_high_points(country)

        # print('Reproject raster')
        # reproject_raster()

        # print('Run viewsheds')
        # process_viewsheds(country)

        print('Processing LOS lookup')
        export_los_lookup(country)

    print('Preprocessing complete')
