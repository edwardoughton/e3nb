###VISUALISE MODEL OUTPUTS###
library(tidyverse)
library(ggpubr)

folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder = file.path(folder, '..', 'data', 'intermediate', 'model_inputs')

#########
folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder = file.path(folder, '..', 'data', 'intermediate', 'model_inputs')

filename = 'rp_by_distance.csv'
data <- read.csv(file.path(folder, filename))

data$frequency_category = factor(data$frequency_category,
                                 levels=c("6-8 GHz",
                                          "11-15 GHz",
                                          "15-18 GHz"),
                                 labels=c("6-8",
                                          "11-15",
                                          "15-18"))

data$distance_category = factor(data$distance_category,
                                levels=c("<10 km",
                                         "10-25 km",
                                         "25-45 km"))

plot1 = 
  ggplot(data, aes(received_power_db, frequency_category)) + coord_flip() +
  geom_boxplot() + geom_jitter(width = 0.5, size=.05, alpha=.2) +
  labs(title="(A) Simulation Results for the Received Signal based on the FSPL",
       colour=NULL,
       subtitle = "Reported for all frequency and distance categories",
       x = 'Received Signal (dB)', y = "Frequency (GHz)") +
  scale_x_continuous(expand = c(0, 0), limits = c(-40,5)) +
  facet_wrap(~distance_category)

########
filename = 'fresnel_clearances.csv'
data <- read.csv(file.path(folder, filename))

data$frequency_category = factor(data$frequency_category,
                                 levels=c("6-8 GHz",
                                          "11-15 GHz",
                                          "15-18 GHz"),
                                 labels=c("6-8",
                                          "11-15",
                                          "15-18"))

plot2 =
  ggplot(data, aes(clearance, frequency_category)) + coord_flip() +
  geom_boxplot() + geom_jitter(width = 0.5, size=.05, alpha=.2) +
  labs(title="(B) Simulation Results for Required Fresnel Clearance Values",
       colour=NULL,
       subtitle = "Reported for all frequency and distance categories",
       x = 'Clearance (M)', y = "Frequency (GHz)") +
  scale_x_continuous(expand = c(0, 0), limits = c(0,23)) +
  facet_wrap(~distance_category)

combined <- ggarrange(plot1, plot2,   
                      ncol = 1, nrow = 2)

folder <- dirname(rstudioapi::getSourceEditorContext()$path)
path = file.path(folder, 'figures', 'panel_plot.png')
ggsave(path, units="in", width=7, height=5, dpi=300)
print(combined)
dev.off()

#########################################
#get folder directory
folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder_inputs = file.path(folder, '..', 'results')

data_per = read.csv(file.path(folder_inputs, 'PER', 'gid_3_aggregated_costs.csv'))
data_per$country = "Peru (PER)"
data_idn = read.csv(file.path(folder_inputs, 'IDN', 'gid_3_aggregated_costs.csv'))
data_idn$country = ifelse(grepl("Papua", data_idn$names), 
                          "Papua (IDN)", "Kalimantan (IDN)")

data = rbind(data_per, data_idn)
remove(data_per, data_idn)

data = data %>%
  group_by(country) %>%
  mutate(id_decile = ntile(id_range_m, 10),
         pop_d_decile = ntile(-pop_density_km2, 10),)

data$strategy = factor(data$strategy,
                           levels=c('clos', 'nlos'),
                           labels=c('CLOS-Only', 'Hybrid CLOS-NLOS'))

data$id_decile = as.factor(as.character(data$id_decile))
data$id_decile = factor(data$id_decile,
                           levels=c(1,2,3,4,5,6,7,8,9,10),
                           labels=c(1,2,3,4,5,6,7,8,9,10))

data$pop_d_decile = as.factor(as.character(data$pop_d_decile))
data$pop_d_decile = factor(data$pop_d_decile,
                           levels=c(1,2,3,4,5,6,7,8,9,10),
                           labels=c(1,2,3,4,5,6,7,8,9,10))

data1 = data %>%
        group_by(country, strategy, pop_d_decile) %>%
        summarise(
          cost_usd = sum(cost_usd),
          population = sum(population),
          area_km2 = sum(area_km2),
          covered_population = sum(covered_population),
          uncovered_population = sum(uncovered_population),
        )

data1$pop_density_km2 = data1$population / data1$area_km2

data1 <- data1[order(data1$country, data1$strategy, data1$pop_d_decile),]

cost_summary <- data1 %>%
  group_by(country, strategy) %>%
    summarize(cost = round(sum(cost_usd / 1e6), 1)
  )

path = file.path(folder, 'figures', 'summarized_data.csv')
write.csv(cost_summary, path)
      
path = file.path(folder, 'figures', 'decile_data.csv')
write.csv(data1, path)

data1 <- data1 %>%
  group_by(country, strategy) %>%
  mutate(cumulative_cost = cumsum(round(cost_usd / 1e6, 3)),
        cumulative_covered = cumsum(round(covered_population / 1e6, 3)),
        uncumulative_covered = cumsum(round(uncovered_population / 1e6, 3)),
        )

plot1 = ggplot(data1, aes(x=pop_d_decile, y=cumulative_cost, 
                          colour=strategy, group=strategy)) +
  geom_line() +
  scale_fill_brewer(palette="Spectral", name = expression('Cost Type'), direction=1) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1), legend.position = "bottom") + 
  labs(title = "(A) Cumulative Investment Cost by Population Density Deciles", 
       colour=NULL,
       subtitle = "Deciles labelled from the highest density to the lowest (1-10)", 
       x = "Population Density Deciles", 
       y = "Cost (Millions $USD)") +
  facet_wrap(~country, scales = "free", ncol=3)

data2 = data %>%
  group_by(country, strategy, id_decile) %>%
  summarise(
    cost_usd = sum(cost_usd),
    covered_population = sum(covered_population),
    uncovered_population = sum(uncovered_population),
  )

data2 <- data2[order(data2$country, data2$strategy, data2$id_decile),]

data2 <- data2 %>%
  group_by(country, strategy) %>%
  mutate(cumulative_cost = cumsum(round(cost_usd / 1e6, 3)),
         cumulative_covered = cumsum(round(covered_population / 1e6, 3)),
         uncumulative_covered = cumsum(round(uncovered_population / 1e6, 3)),
  )

plot2 = ggplot(data2, aes(x=id_decile, y=cumulative_cost, 
                          colour=strategy, group=strategy)) +
  geom_line() +
  scale_fill_brewer(palette="Spectral", name = expression('Cost Type'), direction=1) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1), legend.position = "bottom") + 
  labs(title = "(B) Cumulative Investment Cost by Terrain Irregularity Deciles", 
       colour=NULL,
       subtitle = "Deciles labelled from the lowest terrain ireggularity to the highest (1-10)", 
       x = "Terrain Irregularity Deciles", 
       y = "Cost (Millions $USD)") +
  facet_wrap(~country, scales = "free", ncol=3)

combined <- ggarrange(plot1, plot2, ncol = 1, nrow = 2)

path = file.path(folder, 'figures', 'results_panel.png')
ggsave(path, units="in", width=7, height=6, dpi=300)
print(plot)
dev.off()

#aggregate and export data
aggregated_data = data %>% 
  group_by(strategy, country) %>% 
    summarise(population_m = round(sum(population)/1e6),
              area_km2 = round(sum(area_km2)),
              cost_usd_m = round(sum(cost_usd)/1e6))

aggregated_data$cost_per_user_passed = round(aggregated_data$cost_usd_m / 
  aggregated_data$population_m) 

path = file.path(folder, 'figures', 'aggregated_data.csv')
write.csv(aggregated_data, path)

#############################################################
#get folder directory
folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder_inputs = file.path(folder, '..', 'data', 'intermediate')

data1 = read.csv(file.path(folder_inputs, 'PER', 'los_lookup.csv'))
data1$iso3 = 'PER'
data2 = read.csv(file.path(folder_inputs, 'IDN', 'los_lookup.csv'))
data2$iso3 = 'IDN'

data = rbind(data1, data2)

remove(data1, data2)

data = select(data, iso3, decile, clos_probability, distance_lower, 
              distance_upper)

data$clos_probability = as.numeric(as.character(data$clos_probability))

data[is.na(data)] <- 0

data$distance_mid_km = (data$distance_lower + 
                          ((data$distance_upper - data$distance_lower) / 2)) / 1e3 

data$decile = factor(data$decile, levels=c(1,2,3,4,5,6,7,8,9,10),
                     labels=c('Decile 1',
                              'Decile 2',
                              'Decile 3',
                              'Decile 4',
                              'Decile 5',
                              'Decile 6',
                              'Decile 7',
                              'Decile 8',
                              'Decile 9',
                              'Decile 10'
                     ))

data$iso3 = factor(data$iso3,
                       levels=c('IDN', 'PER'),
                       labels=c('Indonesia (IDN)', 'Peru (PER)'))

plot = ggplot(data, aes(x=distance_mid_km, y=clos_probability, group=iso3)) + 
  geom_point(aes(shape=iso3, color=iso3), size=1) +
  geom_line(aes(color=iso3, linetype=iso3),size=.5) +
  scale_color_manual(values=c("#D55E00", "#0072B2")) +
  labs(title = "CLOS Probability by Terrain Irregularity Deciles",
       subtitle = 'Deciles labelled from the lowest terrain ireggularity to the highest (1-10)',
       x = 'Distance (km)',
       y = "CLOS Probability (Mean)") +
  theme(axis.text.x = element_text(angle = 45), 
        legend.position = "bottom", legend.title=element_blank()) +
  guides(shape=guide_legend(), colour=guide_legend()) +
  facet_wrap(~decile, ncol=5)

path = file.path(folder, 'figures', 'clos_probability.png')
ggsave(path, units="in", width=7, height=4, dpi=300)
print(plot)
dev.off()

#################################
###COST OUTPUTS###
#get folder directory
folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder_inputs = file.path(folder, '..', 'results')

#get peru cost data
data_per = read.csv(file.path(folder_inputs, 'PER', 'cost_item_results.csv'))
data_per$country = "Peru (PER)"

per_deciles = select(data_per, modeling_region, pop_density_km2)
per_deciles = unique(per_deciles)
per_deciles$pop_d_decile <- cut(per_deciles$pop_density_km2, 
                                breaks = quantile(per_deciles$pop_density_km2, probs = seq(0, 1, 0.1)), 
                                labels = 10:1, include.lowest = TRUE)
per_deciles$modeling_region = NULL
data_per <- merge(data_per,per_deciles,by="pop_density_km2")

#get indonesia cost data
folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder_inputs = file.path(folder, '..', 'results')

data_idn = read.csv(file.path(folder_inputs, 'IDN', 'cost_item_results.csv'))
data_idn$country = ifelse(grepl("Papua", data_idn$names), 
                          "Papua (IDN)", "Kalimantan (IDN)")

papua = data_idn[data_idn$country == 'Papua (IDN)',]
kalimantan = data_idn[data_idn$country == 'Kalimantan (IDN)',]

###papua
papua_deciles = select(papua, modeling_region, pop_density_km2)
papua_deciles = unique(papua_deciles)
papua_deciles$pop_d_decile <- cut(papua_deciles$pop_density_km2, 
                                  breaks = quantile(papua_deciles$pop_density_km2, 
                                                    probs = seq(0, 1, 0.1)), 
                                  labels = 10:1, include.lowest = TRUE)
papua_deciles$modeling_region = NULL
papua <- merge(papua,papua_deciles,by="pop_density_km2")

###kalimantan
kalimantan_deciles = select(kalimantan, modeling_region, pop_density_km2)
kalimantan_deciles = unique(kalimantan_deciles)
kalimantan_deciles$pop_d_decile <- cut(kalimantan_deciles$pop_density_km2, 
                                       breaks = quantile(kalimantan_deciles$pop_density_km2, 
                                                         probs = seq(0, 1, 0.1)), 
                                       labels = 10:1, include.lowest = TRUE)
kalimantan_deciles$modeling_region = NULL
kalimantan <- merge(data_idn,kalimantan_deciles,by="pop_density_km2")

###combine
data_idn = rbind(papua, kalimantan)
data = rbind(data_per, data_idn)
remove(data_per, data_idn, papua, kalimantan, per_deciles, papua_deciles, kalimantan_deciles)

data$strategy = factor(data$strategy,
                       levels=c('clos', 'nlos'),
                       labels=c('CLOS-Only', 'Hybrid CLOS-NLOS'))

data$pop_d_decile = as.factor(as.character(data$pop_d_decile))
data$pop_d_decile = factor(data$pop_d_decile,
                           levels=c(1,2,3,4,5,6,7,8,9,10),
                           labels=c(1,2,3,4,5,6,7,8,9,10))

data$cost_usd = data$cost_usd / 1e6

data <- data[!(data$asset_type == "radio_installation"),]

data$asset_type = factor(data$asset_type, levels=c(
  'two_60cm_antennas_usd', 'two_90cm_antennas_usd', 
  'radio_costs_usd',  
  'tower_10_m_usd', 
  'site_survey_and_acquisition', 'power_system'),
  labels=c('Antennas', 'Antennas', 'Radios', 
           'Tower/Transport',
           'Site Survey/Acquisition', 
           'Power System'))

data$strategy = factor(data$strategy, levels=c(
  'CLOS-Only', 'Hybrid CLOS-NLOS'),
  labels=c('CLOS-Only', 'Hybrid CLOS-NLOS'))

totals <- data %>%
  select(country, strategy, pop_d_decile, cost_usd) %>%
  group_by(country, strategy, pop_d_decile) %>%
  summarize(total = round(sum(cost_usd)))

pop_costs = ggplot(data, aes(x=pop_d_decile, y=cost_usd, fill=asset_type)) +
  geom_bar(stat="identity") +
  theme(legend.position = 'bottom') +
  scale_y_continuous(expand = c(0, 0), #breaks = seq(0,60,100),
                     limits = c(0, 110)) +
  labs(colour=NULL,
       title = "(A) Aggregate Cost by Population Density Deciles",
       subtitle = "Deciles labelled from the highest density to the lowest (1-10)",
       x = 'Population Density Deciles', y = "Cost (Millions $USD)", 
       fill='') + #Cost\nType
  theme(panel.spacing = unit(0.6, "lines"), 
        axis.text.x = element_text(angle = 45)) +
  expand_limits(y=0) +
  guides() +
  geom_text(
    aes(pop_d_decile, total + 5, label = total, fill = NULL), #total + 225
    size=2.5, data = totals) +
  facet_grid(strategy~country, scales = "free")

##################
##########ID Range
#get folder directory
folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder_inputs = file.path(folder, '..', 'results')

#get peru cost data
data_per = read.csv(file.path(folder_inputs, 'PER', 'cost_item_results.csv'))
data_per$country = "Peru (PER)"

per_deciles = select(data_per, modeling_region, id_range_m)
per_deciles = unique(per_deciles)
per_deciles$id_decile <- cut(per_deciles$id_range_m, 
                             breaks = quantile(per_deciles$id_range_m, probs = seq(0, 1, 0.1)), 
                             labels = 10:1, include.lowest = TRUE)
per_deciles$modeling_region = NULL
data_per <- merge(data_per,per_deciles,by="id_range_m")

#get indonesia cost data
folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder_inputs = file.path(folder, '..', 'results')

data_idn = read.csv(file.path(folder_inputs, 'IDN', 'cost_item_results.csv'))
data_idn$country = ifelse(grepl("Papua", data_idn$names), 
                          "Papua (IDN)", "Kalimantan (IDN)")

papua = data_idn[data_idn$country == 'Papua (IDN)',]
kalimantan = data_idn[data_idn$country == 'Kalimantan (IDN)',]

###papua
papua_deciles = select(papua, modeling_region, id_range_m)
papua_deciles = unique(papua_deciles)
papua_deciles$id_decile <- cut(papua_deciles$id_range_m, 
                               breaks = quantile(papua_deciles$id_range_m, 
                                                 probs = seq(0, 1, 0.1)), 
                               labels = 10:1, include.lowest = TRUE)
papua_deciles$modeling_region = NULL
papua <- merge(papua,papua_deciles,by="id_range_m")

###kalimantan
kalimantan_deciles = select(kalimantan, modeling_region, id_range_m)
kalimantan_deciles = unique(kalimantan_deciles)
kalimantan_deciles$id_decile <- cut(kalimantan_deciles$id_range_m, 
                                    breaks = quantile(kalimantan_deciles$id_range_m, 
                                                      probs = seq(0, 1, 0.1)), 
                                    labels = 10:1, include.lowest = TRUE)
kalimantan_deciles$modeling_region = NULL
kalimantan <- merge(data_idn,kalimantan_deciles,by="id_range_m")

###combine
data_idn = rbind(papua, kalimantan)
data = rbind(data_per, data_idn)
remove(data_per, data_idn, papua, kalimantan, per_deciles, papua_deciles, kalimantan_deciles)

data$strategy = factor(data$strategy,
                       levels=c('clos', 'nlos'),
                       labels=c('CLOS-Only', 'Hybrid CLOS-NLOS'))

data$id_decile = as.factor(as.character(data$id_decile))
data$id_decile = factor(data$id_decile,
                        levels=c(10,9,8,7,6,5,4,3,2,1),
                        labels=c(1,2,3,4,5,6,7,8,9,10))#

data$cost_usd = data$cost_usd / 1e6

data <- data[!(data$asset_type == "radio_installation"),]

data$asset_type = factor(data$asset_type, levels=c(
  'two_60cm_antennas_usd', 'two_90cm_antennas_usd', 
  'radio_costs_usd', 
  'tower_10_m_usd', 
  'site_survey_and_acquisition', 'power_system'),
  labels=c('Antennas', 'Antennas', 'Radios', 
           'Tower/Transport',
           'Site Survey/Acquisition', 
           'Power System'))

data$strategy = factor(data$strategy, levels=c(
  'CLOS-Only', 'Hybrid CLOS-NLOS'),
  labels=c('CLOS-Only', 'Hybrid CLOS-NLOS'))

totals <- data %>%
  select(country, strategy, id_decile, cost_usd) %>%
  group_by(country, strategy, id_decile) %>%
  summarize(total = round(sum(cost_usd)))

terrain_costs = ggplot(data, aes(x=id_decile, y=cost_usd, fill=asset_type)) +
  geom_bar(stat="identity") +
  theme(legend.position = 'bottom') +
  scale_y_continuous(expand = c(0, 0), #breaks = seq(0,60,100),
                     limits = c(0, 110)) +
  labs(colour=NULL,
       title = "(B) Aggregate Cost by Terrain Irregularity Decile",
       subtitle = "Deciles labelled from the lowest terrain iregularity to the highest (1-10)",
       x = 'Terrain Irregularity Deciles', y = "Cost (Millions $USD)", 
       fill='') + 
  theme(panel.spacing = unit(0.6, "lines"), 
        axis.text.x = element_text(angle = 45)) +
  expand_limits(y=0) +
  guides() +
  geom_text(
    aes(id_decile, total + 5, label = total, fill = NULL), #total + 225
    size=2.5, data = totals) +
  facet_grid(strategy~country, scales = "free")

combined <- ggarrange(pop_costs, terrain_costs,   
                      ncol = 1, nrow = 2,
                      common.legend = TRUE, legend="bottom")

path = file.path(folder, 'figures', 'cost_panel_plot.png')
ggsave(path, units="in", width=7, height=9, dpi=300)
print(combined)
dev.off()

