###VISUALISE MODEL OUTPUTS###
library(tidyverse)
library(ggpubr)

#get folder directory
folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder_inputs = file.path(folder, '..', 'results')

data_per = read.csv(file.path(folder_inputs, 'PER', 'costs_by_settlement.csv'))
data_per$country = "Peru (PER)"
data_idn = read.csv(file.path(folder_inputs, 'IDN', 'costs_by_settlement.csv'))
data_idn$country = ifelse(grepl("Papua", data_idn$names), 
                          "Papua (IDN)", "Kalimantan (IDN)")

data = rbind(data_per, data_idn)
remove(data_per, data_idn)

data = data %>%
  mutate(decile = ntile(id_range_m, 10))

data$decile = as.factor(as.character(data$decile))

data$type = factor(data$type, levels=c("<0.5k",
                                             '0.5-1k',
                                             '1-5k',
                                             '5-10k',
                                             '10-20k',
                                             '>20k'))

ggplot(data, aes(x=type, y=population)) + 
  geom_boxplot()+
  geom_jitter(cex = 0.2, position=position_jitter(0.25)) +
  labs(title = "Peru: Wireless Backhaul Cost per Person Covered", 
       x = 'Settlement Size (Number of Inhabitants)', 
       y = "Cost per Person Covered ($USD)") +
  facet_wrap(country~decile)

path = file.path(folder, 'figures', 'cost_per_pop_covered.png')
ggsave(path, units="in", width=7, height=5.5, dpi=300)
print(plot)
dev.off()
