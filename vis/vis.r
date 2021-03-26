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
