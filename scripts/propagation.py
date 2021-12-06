"""
Estimate Fresnel clearance.

"""
import os
import configparser
import math
import random
import pandas as pd
import numpy as np

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')


def run(distances, frequencies, iterations, directory):
    """
    Run script.

    """
    pt = 20
    gt = 20
    lt = 4
    gr = 20
    lr = 4

    output = []

    distance_categories = set()
    frequency_categories = set()

    for lower_dist, upper_dist in distances:
        for lower_freq, upper_freq in frequencies:

            rand_distances = []
            for i in range(0, iterations):
                rand_distances.append(random.uniform(float(lower_dist), float(upper_dist)))

            rand_frequencies = []

            for i in range(0, iterations):
                rand_frequencies.append(random.uniform(float(lower_freq), float(upper_freq)))

            for rand_distance in rand_distances:

                distance_category = get_distance_category(rand_distance)

                for rand_frequency in rand_frequencies:

                    frequency_category = get_frequency_category(rand_frequency)

                    #calculate Equivalent Isotropically Radiated Power (EIRP)
                    eirp = (
                        float(pt) +
                        float(gt) -
                        float(lt)
                    )

                    fspl = 20*np.log10(rand_distance) + 20*np.log10(rand_frequency) + 32.44

                    received_power = (eirp -
                        fspl +
                        gr -
                        lr
                    )

                    output.append({
                        'distance_category': distance_category,
                        'frequency_category': frequency_category,
                        'frequency_ghz': rand_frequency,
                        'iteration': i,
                        'distance_km': rand_distance,
                        'gain_t_db': gt,
                        'power_t_db': pt,
                        'losses_t_db': lt,
                        'gain_r_db': gr,
                        'losses_r_db': lr,
                        'fspl_db': fspl,
                        'received_power_db': received_power,
                    })

                    frequency_categories.add(frequency_category)

                distance_categories.add(distance_category)

    percentiles = []

    for frequency_category in frequency_categories:
        for distance_category in distance_categories:

            interim = []

            for item in output:
                if (item['frequency_category'] == frequency_category and
                    item['distance_category'] == distance_category):

                    interim.append(item['received_power_db'])

            interim = np.array(interim)

            percentiles.append({
                'distance_category': distance_category,
                'frequency_category': frequency_category,
                'p_1': np.percentile(interim, 1),
                'p_10': np.percentile(interim, 10),
                'p_50': np.percentile(interim, 50),
                'p_90': np.percentile(interim, 90),
                'p_99': np.percentile(interim, 99),
            })

    output = pd.DataFrame(output)
    path = os.path.join(directory, 'rp_by_distance.csv')
    output.to_csv(path, index=False)

    percentiles = pd.DataFrame(percentiles)
    path = os.path.join(directory, 'percentiles_distances.csv')
    percentiles.to_csv(path, index=False)

    return print('Complete FSPL received signal simulation')


def get_distance_category(rand_distance):

    if rand_distance < 10:
        distance_category = '<10 km'
    elif rand_distance >= 10 and rand_distance < 25:
        distance_category = '10-25 km'
    elif rand_distance >= 25 and rand_distance < 45:
        distance_category = '25-45 km'
    else:
        distance_category = 'unallocated distance'
        print('Could not allocate distance category')

    return distance_category

def get_frequency_category(rand_frequency):

    if rand_frequency >= 6 and rand_frequency <= 8:
        frequency_category = '6-8 GHz'
    elif rand_frequency >= 11 and rand_frequency <= 15:
        frequency_category = '11-15 GHz'
    elif rand_frequency >= 15 and rand_frequency < 18:
        frequency_category = '15-18 GHz'
    else:
        frequency_category = 'unallocated frequency'
        print('Could not allocate frequency category')

    return frequency_category


if __name__ == "__main__":

    distances = [
        (0, 10),
        (10, 25),
        (25, 45),
    ]

    frequencies = [
        (6, 8),
        (11, 15),
        (15, 18),
    ]

    iterations = 25

    directory = os.path.join(DATA_INTERMEDIATE, 'model_inputs')

    if not os.path.exists(os.path.dirname(directory)):
        os.makedirs(os.path.dirname(directory))

    run(distances, frequencies, iterations, directory)
