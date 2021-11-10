"""
Estimate Fresnel clearance.

"""
import os
import configparser
import math
import random
import pandas as pd

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')


def run(distances, frequencies, iterations, path):
    """
    Run script.

    """
    output = []

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

                    clearance = 8.66 * math.sqrt(rand_distance / rand_frequency)

                    output.append({
                        'distance_category': distance_category,
                        'frequency_category': frequency_category,
                        'distance_km': rand_distance,
                        'frequency_ghz': rand_frequency,
                        'clearance': clearance,
                    })

    output = pd.DataFrame(output)
    output.to_csv(path, index=False)

    return print('Complete Fresnel simulation')


def get_distance_category(rand_distance):

    if rand_distance < 10:
        distance_category = '<10 km'
    elif rand_distance >= 10 and rand_distance < 25:
        distance_category = '10-25 km'
    elif rand_distance >= 25 and rand_distance < 40:
        distance_category = '25-40 km'
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
        (25, 40),
    ]

    frequencies = [
        (6, 8),
        (11, 15),
        (15, 18),
    ]

    iterations = 500

    path = os.path.join(DATA_INTERMEDIATE, 'model_inputs', 'fresnel_clearances.csv')

    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    run(distances, frequencies, iterations, path)
