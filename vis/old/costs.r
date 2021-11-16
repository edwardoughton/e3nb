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
per_deciles$decile <- cut(per_deciles$pop_density_km2, 
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
papua_deciles$decile <- cut(papua_deciles$pop_density_km2, 
                          breaks = quantile(papua_deciles$pop_density_km2, 
                                            probs = seq(0, 1, 0.1)), 
                          labels = 10:1, include.lowest = TRUE)
papua_deciles$modeling_region = NULL
papua <- merge(papua,papua_deciles,by="pop_density_km2")

###kalimantan
kalimantan_deciles = select(kalimantan, modeling_region, pop_density_km2)
kalimantan_deciles = unique(kalimantan_deciles)
kalimantan_deciles$decile <- cut(kalimantan_deciles$pop_density_km2, 
                          breaks = quantile(kalimantan_deciles$pop_density_km2, 
                                            probs = seq(0, 1, 0.1)), 
                          labels = 10:1, include.lowest = TRUE)
kalimantan_deciles$modeling_region = NULL
kalimantan <- merge(data_idn,kalimantan_deciles,by="pop_density_km2")

###combine
data_idn = rbind(papua, kalimantan)
data = rbind(data_per, data_idn)
remove(data_per, data_idn, papua, kalimantan, per_deciles, papua_deciles, kalimantan_deciles)

deciles_values = data %>% 
  group_by(country, decile) %>% 
  top_n(1, pop_density_km2) 

deciles_values = select(deciles_values, country, decile, pop_density_km2)
deciles_values = unique(deciles_values)

data$cost_usd = data$cost_usd / 1e6

data$asset_type = factor(data$asset_type, levels=c(
  'two_60cm_antennas_usd', 'two_90cm_antennas_usd', 
  'tower_10_m_usd', 'radio_installation',
  'site_survey_and_acquisition', 'power_system', 'cost_freq_for_link_usd'),
  labels=c('Antennas', 'Antennas', 
           'Tower + Transport', 'Radios + Installation', 
           'Site Survey + Acquisition', 
           'Power System', "Frequency Cost"))

data$strategy = factor(data$strategy, levels=c(
  'clos', 'nlos'),
  labels=c('CLOS-only', 'Hybrid CLOS-NLOS'))

# data$country = factor(data$iso3, levels=c(
#   'PER', 'IDN'),
#   labels=c('Peru', 'Indonesia'))

data$decile = factor(data$decile, levels=c(
  '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'),
  labels=c('1', '2', '3', '4', '5', '6', '7', '8', '9', '10'))

totals <- data %>%
  select(country, strategy, decile, cost_usd) %>%
  group_by(country, strategy, decile) %>%
  summarize(total = round(sum(cost_usd)))

costs = ggplot(data, aes(x=decile, y=cost_usd, fill=asset_type)) +
  geom_bar(stat="identity") +
  theme(legend.position = 'bottom') +
  scale_y_continuous(expand = c(0, 0), breaks = seq(0,200,50),
                     limits = c(0, 150)) +
  labs(colour=NULL,
       title = "Cost per Smartphone User for Universal Broadband",
       subtitle = "Results reported by scenario, strategy and population decile",
       x = 'Population Density Decile (Inhabitants km^2', y = "Per Smartphone Cost ($USD)", 
       fill='Cost\nType') +
  theme(panel.spacing = unit(0.6, "lines"), 
        axis.text.x = element_text(angle = 45)) +
  expand_limits(y=0) +
  guides() +
  geom_text(
    aes(decile, total +10, label = total, fill = NULL), #total + 225
    size=2.5, data = totals) +
  facet_grid(strategy~country, scales = "free")

path = file.path(folder, 'figures', 'cost_composition.png')
ggsave(path, units="in", width=7, height=6, dpi=300)
print(costs)
dev.off()
