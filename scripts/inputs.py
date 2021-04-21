"""
All model inputs.

Written by Ed Oughton.

March 2021

"""
countries = [
    {'iso3': 'IDN', 'iso2': 'ID', 'regional_level': 2, 'lowest_regional_level': 3,
        'max_antenna_height': 50, 'region': 'SEA', 'pop_density_km2': 100,
        'settlement_size': 500, 'cluster': 'C1', 'coverage_4G': 16
    },
    {'iso3': 'PER', 'iso2': 'PE', 'regional_level': 2, 'lowest_regional_level': 3,
        'max_antenna_height': 50, 'region': 'SSA', 'pop_density_km2': 25,
        'settlement_size': 500, 'cluster': 'C1', 'coverage_4G': 16
    },
]

strategies = [
    'clos',
    'nlos'
]

rain_region_distances = {
    'clos': {
        'high': 15000, #los link distance in meters
        'moderate': 30000, #los link distance in meters
        'low': 45000 #los link distance in meters
    },
    'nlos': {
        'high': 5000, #nlos link distance in meters
        'moderate': 10000, #nlos link distance in meters
        'low': 15000 #nlos link distance in meters
    },
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
    '25_45':{
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
        'cost_freq_for_link_usd': 6000,
        'two_60cm_antennas_usd': 600,
        'site_survey_and_acquisition': 2400,
        'tower_0_10_m_usd': 25000,
        'tower_10_20_m_usd': 35000,
        'tower_20_30_m_usd': 45000,
        'radio_installation': 10000,
        'power_system': 10000,
    },
    '10_20': {
        'two_90cm_antennas_usd': 1200,
        'site_survey_and_acquisition': 2400,
        'tower_0_10_m_usd': 25000,
        'tower_10_20_m_usd': 35000,
        'tower_20_30_m_usd': 45000,
        'radio_installation': 10000,
        'power_system': 10000,
    },
    '20_30': {
        'cost_freq_for_link_usd': 6000,
        'two_120cm_antennas_usd': 2400,
        'site_survey_and_acquisition': 2400,
        'tower_0_10_m_usd': 25000,
        'tower_10_20_m_usd': 35000,
        'tower_20_30_m_usd': 45000,
        'radio_installation': 10000,
        'power_system': 10000,
    },
    '30_45': {
        'cost_freq_for_link_usd': 6000,
        'two_180cm_antennas_usd': 4800,
        'site_survey_and_acquisition': 2400,
        'tower_0_10_m_usd': 25000,
        'tower_10_20_m_usd': 35000,
        'tower_20_30_m_usd': 45000,
        'radio_installation': 10000,
        'power_system': 10000,
    }
}
