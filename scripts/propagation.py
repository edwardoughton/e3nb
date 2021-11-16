"""
Propagation modeling to estimate received signal
based on different distances and frequencies.

"""
import os
import configparser
import numpy as np
from math import pi, sqrt
import random
import pandas as pd

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')


def propagation():
    """

    """
    iterations = 100
    distance_max = 60
    frequencies = 8, 15, 18
    pt = 20
    gt = 20
    lt = 4
    gr = 20
    lr = 4

    #calculate Equivalent Isotropically Radiated Power (EIRP)
    eirp = (
        float(pt) +
        float(gt) -
        float(lt)
    )

    output = []

    for frequency in frequencies:
        for i in range(0, iterations):

            d = random.uniform(float(0), float(distance_max))

            fspl = 20*np.log10(d) + 20*np.log10(frequency) + 32.44 #- gt - gr

            received_power = (eirp -
                fspl +
                gr -
                lr
            )

            output.append({
                'frequency_ghz': frequency,
                'iteration': i,
                'distance_km': d,
                'gain_t_db': gt,
                'power_t_db': pt,
                'losses_t_db': lt,
                'gain_r_db': gr,
                'losses_r_db': lr,
                'fspl_db': fspl,
                'received_power_db': received_power,
            })

    directory = os.path.join(DATA_INTERMEDIATE, 'model_inputs')

    if not os.path.exists(os.path.dirname(directory)):
        os.makedirs(os.path.dirname(directory))

    output = pd.DataFrame(output)
    path = os.path.join(directory, 'propagation_results.csv')
    output.to_csv(path, index=False)

    return print('Completed free space path loss simulation')


if __name__ == '__main__':

    propagation()
