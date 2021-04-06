###VISUALISE MODEL OUTPUTS###
library(tidyverse)
library(ggpubr)

#get folder directory
folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder_inputs = file.path(folder, '..', 'results')

data = read.csv(file.path(folder_inputs, 'PER', 'costs_by_settlement.csv'))

data$type = factor(data$type, levels=c("<0.5k",
                                             '0.5-1k',
                                             '1-5k',
                                             '5-10k',
                                             '10-20k',
                                             '>20k'))

plot = ggplot(data, aes(x=type, y=cost_per_pop_covered)) + 
  geom_boxplot()+
  geom_jitter(cex = 0.2, position=position_jitter(0.25)) +
  labs(title = "Peru: Wireless Backhaul Cost per Person Covered", 
       x = 'Settlement Size (Number of Inhabitants)', 
       y = "Cost per Person Covered ($USD)") 

path = file.path(folder, 'figures', 'cost_per_pop_covered.png')
ggsave(path, units="in", width=7, height=5.5, dpi=300)
print(plot)
dev.off()

#get folder directory
folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder_inputs = file.path(folder, '..', 'data', 'intermediate')

data1 = read.csv(file.path(folder_inputs, 'PER', 'los_lookup.csv'))
data1$iso3 = 'PER'
data2 = read.csv(file.path(folder_inputs, 'IDN', 'los_lookup.csv'))
data2$iso3 = 'IDN'

data = rbind(data1, data2)

remove(data1, data2)

data$distance_mid_km = (data$distance_lower + 
                          ((data$distance_upper - data$distance_lower) / 2)) / 1e3 

data$decile = factor(data$decile, levels=c(0,1,2,3,4,5,6,7,8,9),
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

plot = ggplot(data, aes(x=distance_mid_km, y=nlos_probability, group=iso3)) + 
  geom_point(aes(shape=iso3, color=iso3), size=.75) +
  geom_line(aes(color=iso3, linetype=iso3),size=.75) +
  scale_color_manual(values=c("#D55E00", "#0072B2")) + 
  scale_linetype_manual(values=c("dashed", "dotted"))+
  labs(title = "NLOS Probability by Terrain Irregularity Deciles",
       x = 'Distance (km)',
       y = "NLOS Probability (Mean)") +
  theme(axis.text.x = element_text(angle = 45), 
        legend.position = "bottom", legend.title=element_blank()) +
  guides(shape=guide_legend(), colour=guide_legend()) +
  facet_wrap(~decile, ncol=2)


path = file.path(folder, 'figures', 'nlos_probability.png')
ggsave(path, units="in", width=6, height=7, dpi=300)
print(plot)
dev.off()
