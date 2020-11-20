"""
Run script

"""
import os
import configparser
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, mapping, shape
import random
import rasterio
import networkx as nx

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
RESULTS = os.path.join(BASE_PATH, '..', 'results')


def run_country(country):
    """

    """
    iso3 = country['iso3']
    max_distance = 40000

    filename = '10S090W_20101117_gmted_med300.tif'
    path_input = os.path.join(DATA_RAW, 'gmted', filename)

    folder_out_shapes = os.path.join(RESULTS, iso3, 'shapes')

    if not os.path.exists(folder_out_shapes):
        os.makedirs(folder_out_shapes)

    folder_out_viewsheds = os.path.join(RESULTS, iso3, 'viewsheds')

    if not os.path.exists(folder_out_viewsheds):
        os.makedirs(folder_out_viewsheds)

    path = os.path.join(DATA_INTERMEDIATE, iso3, 'buffer_routing_zones', 'edges')
    all_paths = glob.glob(path + '/*.shp')#[:1]

    for path in all_paths:

        output = []

        routing_structures = gpd.read_file(path, crs='epsg:4326')

        for idx, routing_structure in routing_structures.iterrows():

            path_output = os.path.join(folder_out_viewsheds, os.path.basename(path)[:-4])

            routing_structure = gpd.GeoDataFrame({'geometry': [routing_structure['geometry']]}, index=[0])
            routing_structure = routing_structure.set_crs('epsg:4326')
            routing_structure = routing_structure.to_crs('epsg:3857')
            routing_structure['length'] = routing_structure['geometry'].length

            point_start = routing_structure['geometry'][0].coords[0]
            point_end = routing_structure['geometry'][0].coords[-1]

            new_routing_nodes = []

            new_routing_nodes.append(point_start)
            new_routing_nodes.append(point_end)

            # if not round(routing_structure['length'][0]) < 7248:
            #     continue

            if routing_structure['length'][0] <= max_distance:

                start = point_start
                end = point_end

                new_routing_node = find_next_short_distance_routing_node(routing_structure, start, end,
                    path_input, path_output, max_distance, folder_out_shapes)

                if len(new_routing_nodes) > 0:
                    new_routing_nodes.append(new_routing_node)

            else:

                while not point_end == point_start:

                    line = LineString([point_start, point_end])

                    if line.length < max_distance:
                        point_end = point_start
                        new_routing_nodes.append(point_start)
                        new_routing_nodes.append(point_end)
                        continue

                    intermediate_point = line.interpolate(max_distance).coords[0]

                    start = point_start
                    end = intermediate_point
                    print('working on {} and {}'.format(start, end))

                    new_routing_node = find_next_long_distance_routing_node(routing_structure, start, end,
                        path_input, path_output, max_distance, folder_out_shapes)

                    new_routing_nodes.append(new_routing_node)

                    point_start = new_routing_node

            # output = []

            for item in new_routing_nodes:

                output.append({
                    'type': 'Point',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': item
                    },
                    'properties': {}
                })

        output = gpd.GeoDataFrame.from_features(output, crs='epsg:3857')
        output = output.to_crs('epsg:4326')

        path_nodes = os.path.join(folder_out_shapes, '{}_{}_nodes.shp'.format(point_start[0], point_start[1]))
        output.to_file(path_nodes, crs='epsg:4326')

        path_edges = os.path.join(folder_out_shapes, '{}_{}_edges.shp'.format(point_start[0], point_start[1]))
        fit_edges(path_nodes, path_edges)

    return print('Complete')


def find_next_short_distance_routing_node(routing_structure, point_start, point_end, path_input,
    path_output, max_distance, folder_out_shapes):
    """

    """
    x = point_start[0]
    y = point_start[1]
    point_name = '{}_{}'.format(x, y)

    point_start = Point(point_start)
    point_start = gpd.GeoDataFrame({'geometry': [point_start]}, index=[0])
    point_start = point_start.set_crs('epsg:3857')
    point_start = point_start.to_crs('epsg:4326')
    point_start = point_start['geometry'][0].coords[0]

    file_path = os.path.join(path_output, 'location', 'PERMANENT', 'viewsheds', point_name + '.tif')
    if not os.path.exists(file_path):
        viewshed(point_start, path_input, path_output, point_name, max_distance, 'epsg:4326')

    if check_los(file_path, point_end) == 'los':
        return []

    point_start = Point(point_start)
    point_start = gpd.GeoDataFrame({'geometry': [point_start]}, index=[0])
    point_start = point_start.set_crs('epsg:4326')
    point_start = point_start.to_crs('epsg:3857')

    shape_area = gpd.GeoDataFrame.from_features([{
        'geometry': {
            'type': 'LineString',
            'coordinates': ([
                point_start['geometry'][0].coords[0],
                point_end#[0]
            ])
        },
        'properties': {}
    }], crs='epsg:3857')

    shape_area['geometry'] = shape_area['geometry'].buffer(5000)
    filename = os.path.join(folder_out_shapes, '{}_{}_poly.shp'.format(x, y))
    shape_area.to_file(filename, crs='epsg:3857')

    grid = generate_grid(shape_area, 1000, 1000)

    filename = os.path.join(folder_out_shapes, '{}_{}_grid.shp'.format(x, y))
    grid.to_file(filename, crs='epsg:3857')
    grid = grid.to_crs('epsg:4326')

    shape_area = shape_area.to_crs('epsg:4326')
    path_viewsheds = os.path.join(path_output, 'location', 'PERMANENT', 'viewsheds', point_name + '.tif')
    new_routing_node = snap_to_equidistant_high_point(grid, path_viewsheds, shape_area, point_start, point_end, folder_out_shapes)

    return new_routing_node


def check_los(path_input, point):
    """
    Find potential LOS high points.

    """
    with rasterio.open(path_input) as src:

        x = point[0]
        y = point[1]

        for val in src.sample([(x, y)]):
            if np.isnan(val):
                return 'nlos'
            else:
                return 'nlos'
                # print('Did not recognize los type (neither 1 nor 0)')


def find_next_long_distance_routing_node(routing_structure, point_start, point_end, path_input,
    path_output, max_distance, folder_out_shapes):
    """

    """
    x = point_start[0]
    y = point_start[1]
    point_name = '{}_{}'.format(x, y)

    point_start = Point(point_start)
    point_start = gpd.GeoDataFrame({'geometry': [point_start]}, index=[0])
    point_start = point_start.set_crs('epsg:3857')
    point_start = point_start.to_crs('epsg:4326')
    point_start = point_start['geometry'][0].coords[0]

    if not os.path.exists(os.path.join(path_output, 'location', 'PERMANENT', 'viewsheds', point_name + '.tif')):
        viewshed(point_start, path_input, path_output, point_name, max_distance, 'epsg:4326')

    point_start = Point(point_start)
    point_start = gpd.GeoDataFrame({'geometry': [point_start]}, index=[0])
    point_start = point_start.set_crs('epsg:4326')
    point_start = point_start.to_crs('epsg:3857')

    shape_area = gpd.GeoDataFrame.from_features([{
        'geometry': {
            'type': 'LineString',
            'coordinates': ([
                point_start['geometry'][0].coords[0],
                point_end#[0]
            ])
        },
        'properties': {}
    }], crs='epsg:3857')

    shape_area['geometry'] = shape_area['geometry'].buffer(5000)

    filename = os.path.join(folder_out_shapes, '{}_{}_poly.shp'.format(x, y))
    shape_area.to_file(filename, crs='epsg:3857')

    grid = generate_grid(shape_area, 1000, 1000)

    filename = os.path.join(folder_out_shapes, '{}_{}_grid.shp'.format(x, y))
    grid.to_file(filename, crs='epsg:3857')
    grid = grid.to_crs('epsg:4326')

    shape_area = shape_area.to_crs('epsg:4326')
    path_viewsheds = os.path.join(path_output, 'location', 'PERMANENT', 'viewsheds', point_name + '.tif')
    new_routing_node = snap_to_furthest_high_point(grid, path_viewsheds, shape_area, point_start)

    return new_routing_node


def viewshed(point, path_input, path_output, tile_name, max_distance, crs):
    """
    Perform a viewshed using GRASS.

    """
    print(point)
    with Session(gisdb=path_output, location="location", create_opts=crs):

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
        gcore.run_command('r.viewshed', flags='e',
                input=tile_name,
                output='{}.tif'.format(tile_name),
                coordinate= [point[0], point[1]],
                observer_elevation=30,
                target_elevation=30,
                memory=5000,
                overwrite=True,
                quiet=True,
                max_distance=max_distance,
                # verbose=True
        )

def generate_grid(shape_area, x_length, y_length):
    """
    Generate a spatial grid.

    """
    xmin, ymin, xmax, ymax = shape_area.total_bounds

    length = x_length #1e5
    wide = y_length #1e5

    cols = list(range(int(np.floor(xmin)), int(np.ceil(xmax + wide)), int(wide)))
    rows = list(range(int(np.floor(ymin)), int(np.ceil(ymax + length)), int(length)))
    rows.reverse()

    polygons = []
    for x in cols:
        for y in rows:
            polygons.append(Polygon([(x,y), (x+wide, y), (x+wide, y-length), (x, y-length)]))

    #create grid as geopandas dataframe
    grid = gpd.GeoDataFrame({'geometry': polygons}, crs='epsg:3857')

    #add grid id column and copy
    grid['id'] = grid.index

    #copy dataframe and convert to centroids
    centroids = grid.copy()
    centroids['geometry'] = centroids['geometry'].representative_point()

    #get centroids within national boundary and select just id column
    centroids = gpd.overlay(centroids, shape_area, how='intersection')
    centroids = centroids[['id']]

    #get those grid polygons which intersect with centroids
    grid = pd.merge(grid, centroids, on='id', how='inner')

    #convert back to WGS85 and remove null geometries
    grid.crs = "epsg:3857"
    # grid = grid.to_crs("epsg:4326")
    # grid = grid[grid.geometry.notnull()]

    # grid.to_file(os.path.join(folder, os.path.basename(path)[:-4] + '.shp'))
    grid['geometry'] = grid['geometry'].representative_point()

    return grid

def snap_to_equidistant_high_point(grid, path_input, shape_area, point_start, point_end,
    folder_out_shapes):
    """
    Find potential LOS high points.

    """
    all_points = []

    for idx, point in grid.iterrows():

        with rasterio.open(path_input) as src:

            x = point['geometry'].coords[0][0]
            y = point['geometry'].coords[0][1]

            for val in src.sample([(x, y)]):
                if np.isnan(val):
                    continue
                else:
                    all_points.append({
                        'type': 'Point',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': (x, y)
                            },
                        'properties': {
                            'elevation_m': val[0]
                        },
                    })

    all_points = gpd.GeoDataFrame.from_features(all_points, crs='epsg:4326')

    all_points = gpd.overlay(all_points, shape_area, how='intersection')

    all_points = all_points.to_crs('epsg:3857')
    # all_points.to_file(os.path.join(folder_out_shapes, 'options.shp'), crs='epsg:3857')
    all_linestrings = []

    for idx, point in all_points.iterrows():

        line = LineString([
            (point_start['geometry'][0].coords[0][0], point_start['geometry'][0].coords[0][1]),
            (point['geometry'].coords[0][0], point['geometry'].coords[0][1]),
            point_end
        ])

        all_linestrings.append({
            'type': 'LineString',
            'geometry': mapping(line),
            'properties': {
                'elevation_m': point['elevation_m']
            }
        })

    all_linestrings = gpd.GeoDataFrame.from_features(all_linestrings, crs='epsg:3857')

    all_linestrings['length'] = all_linestrings['geometry'].length

    furthest_point_geodf = (all_linestrings[all_linestrings['length'] == all_linestrings['length'].min()])
    # furthest_point_geodf.to_file(os.path.join(folder_out_shapes, 'test.shp'), crs='epsg:3857')
    return list(furthest_point_geodf.geometry.iloc[0].coords[1])


def snap_to_furthest_high_point(grid, path_input, shape_area, point_start):
    """
    Find potential LOS high points.

    """
    all_points = []

    for idx, point in grid.iterrows():

        with rasterio.open(path_input) as src:

            x = point['geometry'].coords[0][0]
            y = point['geometry'].coords[0][1]

            for val in src.sample([(x, y)]):
                if val == 1:
                    all_points.append({
                        'type': 'Point',
                        'geometry': {
                            'type': 'Point',
                            'coordinates': (x, y)
                            },
                        'properties': {},
                    })

    all_points = gpd.GeoDataFrame.from_features(all_points, crs='epsg:4326')

    all_points = gpd.overlay(all_points, shape_area, how='intersection')

    all_points = all_points.to_crs('epsg:3857')

    all_linestrings = []

    for idx, point in all_points.iterrows():

        line = LineString([
            (point_start['geometry'][0].coords[0][0], point_start['geometry'][0].coords[0][1]),
            (point['geometry'].coords[0][0], point['geometry'].coords[0][1])
        ])

        all_linestrings.append({
            'type': 'LineString',
            'geometry': mapping(line),
            'properties': {}
        })

    all_linestrings = gpd.GeoDataFrame.from_features(all_linestrings, crs='epsg:3857')

    all_linestrings['length'] = all_linestrings['geometry'].length

    furthest_point_geodf = (all_linestrings[all_linestrings['length'] == all_linestrings['length'].max()])

    return list(furthest_point_geodf.geometry.iloc[0].coords[1])


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
