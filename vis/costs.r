###VISUALISE MODEL OUTPUTS###
library(tidyverse)
library(ggpubr)

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
  'cost_freq_for_link_usd', #or radio_costs_usd
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
  'cost_freq_for_link_usd', #or radio_costs_usd
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

