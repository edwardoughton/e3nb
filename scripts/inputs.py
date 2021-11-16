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

cost_dist = {
    '0_10': {
        'radio_costs_usd': 6000,
        'two_60cm_antennas_usd': 1200,
        'site_survey_and_acquisition': 8700,
        'tower_10_m_usd': 10000,
        # 'radio_installation': 10000,
        'power_system': 12000,
    },
    '10_20': {
        'radio_costs_usd': 6000,
        'two_90cm_antennas_usd': 2200,
        'site_survey_and_acquisition': 8700,
        'tower_10_m_usd': 10000,
        # 'radio_installation': 10000,
        'power_system': 12000,
    },
    '20_30': {
        'radio_costs_usd': 6000,
        'two_120cm_antennas_usd': 3600,
        'site_survey_and_acquisition': 8700,
        'tower_10_m_usd': 10000,
        # 'radio_installation': 10000,
        'power_system': 12000,
    },
    '30_45': {
        'radio_costs_usd': 6000,
        'two_180cm_antennas_usd': 4460,
        'site_survey_and_acquisition': 8700,
        'tower_10_m_usd': 10000,
        # 'radio_installation': 10000,
        'power_system': 12000,
    }
}
