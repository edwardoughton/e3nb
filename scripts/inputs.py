"""
All model inputs.

Written by Ed Oughton.

March 2021

"""
countries = [
    {'iso3': 'PER', 'iso2': 'PE', 'regional_level': 2, 'max_antenna_height': 30,
        'buffer_size_m': 5000, 'grid_width_m': 1000, 'region': 'SSA',
        'pop_density_km2': 25, 'settlement_size': 500, 'subs_growth': 3.5,
        'smartphone_growth': 5, 'cluster': 'C1', 'coverage_4G': 16
    },
]

rain_regions = {
    'high': 5000, #meters
    'moderate': 10000,
    'low': 15000
}

frequency_lookup = {
    'under_10km': 18, #GHz
    'under_20km': 15, #GHz
    'under_45km': 8, #GHz
}

fresnel_lookup = {
    '0_10':{ #key is by distance (km)
        #key: X_Y_ is range freq X to freq Y
        #value: meters clearance from ground
        '6_8_nofoliage': 15,
        '6_8_foliage': 25,
        '11_15_nofoliage': 13,
        '11_15_foliage': 23,
        '15_18_nofoliage': 12,
        '15_18_foliage': 22
    },
    '10_25':{
        '6_8_nofoliage': 19,
        '6_8_foliage': 29,
        '11_15_nofoliage': 16,
        '11_15_foliage': 26,
        '15_18_nofoliage': 13,
        '15_18_foliage': 23
    },
    '25_40':{
        '6_8_nofoliage': 19,
        '6_8_foliage': 29,
        '11_15_nofoliage': 16,
        '11_15_foliage': 26,
        '15_18_nofoliage': 13,
        '15_18_foliage': 23
    },
}

cost_dist = {
    '0_10': {
        'two_0.6m_antennas_usd': 600,
        'tower_usd': 25000,
        'power_system': 10000,
    },
    '10_20': {
        'antenna_size_m': 0.9,
        'cost_each_usd': 600,
        'cost_for_link_usd': 1200,
        'tower_usd': 25000,
        'power_system': 10000,
    },
    '20_30': {
        'antenna_size_m': 1.2,
        'cost_each_usd': 1200,
        'cost_for_link_usd': 2400,
        'tower_usd': 25000,
        'power_system': 10000,
    },
    '30_40': {
        'antenna_size_m': 1.8,
        'cost_each_usd': 2400,
        'cost_for_link_usd': 4800,
        'tower_usd': 25000,
        'power_system': 10000,
    }
}

cost_freq = {
    '6_8': {
        'cost_each_usd': 3000,
        'cost_for_link_usd': 6000,
    },
    '11_13': {
        'cost_each_usd': 3000,
        'cost_for_link_usd': 6000,
    },
    '15_18': {
        'cost_each_usd': 3000,
        'cost_for_link_usd': 6000,
    },
}
