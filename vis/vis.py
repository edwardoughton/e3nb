"""
Visualize the least cost network structure.

Written by Ed Oughton.

November 2020.

"""
import os
import configparser
import numpy as np
import pandas as pd
import geopandas as gpd
import seaborn as sns
import matplotlib.pyplot as plt
import contextily as ctx

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

RESULTS = os.path.join(BASE_PATH, '..', 'results')
VIS_FIGURES = os.path.join(BASE_PATH, '..', 'vis', 'figures')

def vis():
    """
    Visualize results.

    """
    strategy = [
        ('clos', 'CLOS-only\n(Red: Settlements, Yellow: Towers)'),
        ('nlos', 'Hybrid CLOS-NLOS\n(Red: Settlements, Yellow: Towers)')
    ]

    path = os.path.join(RESULTS, 'PER', 'edges', 'clos', 'PER.1.3_1.shp')
    clos = gpd.read_file(path, crs='epsg:4326')
    clos['strategy'] = 'clos'

    path = os.path.join(RESULTS, 'PER', 'edges', 'nlos', 'PER.1.3_1.shp')
    nlos = gpd.read_file(path, crs='epsg:4326')
    nlos['strategy'] = 'nlos'

    data = pd.concat([clos, nlos])
    data['Type'] = 'Routing Path'

    filename = 'settlements.shp'
    path = os.path.join(BASE_PATH, 'intermediate', 'PER', 'settlements')
    settlements = gpd.read_file(os.path.join(path, filename), crs='epsg:4326')

    route_buffer = data.copy()
    route_buffer = route_buffer.to_crs('epsg:3857')
    route_buffer['geometry'] = route_buffer['geometry'].buffer(10)
    route_buffer = route_buffer.to_crs('epsg:4326')
    settlements = gpd.overlay(settlements, route_buffer, how='intersection')
    settlements['Type'] = 'Settlements'
    settlements = settlements[['geometry', 'Type']]

    data1 = data.loc[data['strategy'] == strategy[0][0]]
    all_data_as_dicts = data1.to_dict('records')#[:1]

    points = []

    for item in all_data_as_dicts:
        for i in range(0, 2):
            point = item['geometry'].coords[i]
            points.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': point,
                },
                'properties': {
                    'length': item['length'],
                    'link_los': item['link_los'],
                    'status': item['status'],
                    'strategy': item['strategy'],
                    'Type': item['Type'],
                }
            })
    points = gpd.GeoDataFrame.from_features(points, crs='epsg:4326')

    data2 = data.loc[data['strategy'] == strategy[1][0]]
    all_data_as_dicts = data2.to_dict('records')#[:1]

    points2 = []

    for item in all_data_as_dicts:
        for i in range(0, 2):
            point = item['geometry'].coords[i]
            points2.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': point,
                },
                'properties': {
                    'length': item['length'],
                    'link_los': item['link_los'],
                    'status': item['status'],
                    'strategy': item['strategy'],
                    'Type': item['Type'],
                }
            })
    points2 = gpd.GeoDataFrame.from_features(points2, crs='epsg:4326')

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 10))

    settlements.plot(color='red', markersize=15, legend=True, ax=ax1, zorder=15)
    points.plot(color='yellow', markersize=7, legend=True, ax=ax1, zorder=10)
    data.plot(lw=1, legend=True, ax=ax1, zorder=5)

    settlements.plot(color='red', markersize=15, legend=True, ax=ax2, zorder=15)
    points2.plot(color='yellow', markersize=7, legend=True, ax=ax2, zorder=10)
    data.plot(lw=1, legend=True, ax=ax2, zorder=5)

    ax1.title.set_text('{}'.format(strategy[0][1]))
    ax2.title.set_text('{}'.format(strategy[1][1]))
    ctx.add_basemap(ax1, crs=data.crs)
    ctx.add_basemap(ax2, crs=data.crs)

    filename = os.path.join(VIS_FIGURES, 'network_panel_plot.png')
    plt.savefig(filename, pad_inches=0, dpi=100)
    plt.close()

    return print('Completed visualization')


if __name__ == '__main__':

    vis()
