###VISUALISE MODEL OUTPUTS###
library(tidyverse)
library(ggpubr)

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
                           labels=c('Only-CLOS', 'Hybrid CLOS-NLOS'))

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
          covered_population = sum(covered_population),
          uncovered_population = sum(uncovered_population),
        )

data1 <- data1[order(data1$country, data1$strategy, data1$pop_d_decile),]

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
  # scale_linetype_manual(values=c("dashed", "dotted"))+
  labs(title = "CLOS Probability by Terrain Irregularity Deciles",
       subtitle = 'Deciles labelled from the lowest terrain ireggularity to the highest (1-10)',
       x = 'Distance (km)',
       y = "CLOS Probability (Mean)") +
  theme(axis.text.x = element_text(angle = 45), 
        legend.position = "bottom", legend.title=element_blank()) +
  guides(shape=guide_legend(), colour=guide_legend()) +
  facet_wrap(~decile, ncol=2)

path = file.path(folder, 'figures', 'clos_probability.png')
ggsave(path, units="in", width=7, height=6, dpi=300)
print(plot)
dev.off()
