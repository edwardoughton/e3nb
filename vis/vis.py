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

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

RESULTS = os.path.join(BASE_PATH, '..', 'results')
VIS_FIGURES = os.path.join(BASE_PATH, '..', 'vis', 'figures')

def vis(countries):
    """
    Visualize results.

    """
    data_to_plot = []

    for country in countries:

        data = []

        path = os.path.join(RESULTS, country, 'results.csv')
        country_results = pd.read_csv(path)
        country_results = country_results.to_dict('records')

        for item in country_results:
            data.append({
                'country': country,
                'strategy': item['strategy'],
                'population_covered': item['population_covered'] / 1e6,
                'network_cost': item['network_cost'] / 1e9,
                'cost_per_pop': item['cost_per_pop'],
            })

        data = pd.DataFrame(data)

        data = data.sort_values('cost_per_pop')

        data = data[['country', 'strategy', 'population_covered', 'network_cost']]

        los = data.loc[data['strategy'] == 'los']

        los = los.copy()

        population = los['population_covered'].sum()

        los['pop_perc'] = los['population_covered'] / population * 100

        los['pop_cumsum'] = los.groupby(by=['strategy', 'country'])['pop_perc'].cumsum()
        los['cost_cumsum'] = los.groupby(by=['strategy', 'country'])['network_cost'].cumsum()

        nlos = data.loc[data['strategy'] == 'nlos']
        nlos = nlos.copy()

        population = nlos['population_covered'].sum()
        nlos['pop_perc'] = nlos['population_covered'] / population * 100
        nlos['pop_cumsum'] = nlos.groupby(by=['strategy', 'country'])['pop_perc'].cumsum()
        nlos['cost_cumsum'] = nlos.groupby(by=['strategy', 'country'])['network_cost'].cumsum()

        data = los.append(nlos)
        data = data.to_dict('records')

        data_to_plot = data_to_plot + data

    data_to_plot = pd.DataFrame(data_to_plot)

    data_to_plot = data_to_plot[['country', 'strategy', 'pop_cumsum', 'cost_cumsum']]

    data_to_plot.columns = ['Country', 'Strategy', 'Population Covered (%)', 'Cumulative Cost ($USD Billions)']

    data_to_plot['Strategy'] = data_to_plot['Strategy'].map({'los': 'LOS', 'nlos': 'NLOS'})

    plot = sns.relplot(data=data_to_plot,
    x="Population Covered (%)", y="Cumulative Cost ($USD Billions)",hue="Strategy", col="Country",
    kind="line")

    plot.savefig(VIS_FIGURES + '/cost.png', dpi=300)

    data_to_plot.to_csv(os.path.join(VIS_FIGURES, '..', 'vis_data.csv'), index=False)

    return print('Completed visualization')


if __name__ == '__main__':

    # countries = find_country_list(['Africa'])

    # countries = [
    #     {'iso3': 'PER', 'iso2': 'PE', 'regional_level': 2, #'regional_nodes_level': 3,
    #         'region': 'SSA', 'pop_density_km2': 25, 'settlement_size': 500,
    #         'subs_growth': 3.5, 'smartphone_growth': 5, 'cluster': 'C1', 'coverage_4G': 16
    #     },
    # ]

    # for country in countries:

    countries = ['PER', 'IDN']

    vis(countries)
