library(tidyverse)

#get folder directory
folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder = file.path(folder, '..', 'data', 'intermediate', 'model_inputs')

filename = 'fresnel_clearances.csv'
data <- read.csv(file.path(folder, filename))

data$frequency_category = factor(data$frequency_category, 
                        levels=c("6-8 GHz",
                                 "11-15 GHz",
                                 "15-18 GHz"),
                       labels=c("6-8",
                                "11-15",
                                "15-18"))

ggplot(data, aes(clearance, frequency_category)) + coord_flip() +
  geom_boxplot() + geom_jitter(width = 0.1, size=.1) + 
  labs(title="Simulation Results for Required Fresnel Clearance Values", 
  colour=NULL,
  subtitle = "Reported for all frequency and distance categories",
  x = 'Clearance (m)', y = "Frequency (GHz)") +
  facet_wrap(~distance_category)

folder <- dirname(rstudioapi::getSourceEditorContext()$path)
path = file.path(folder, 'figures', 'fresnel_clearances.png')
ggsave(path, units="in", width=7, height=4, dpi=300)
print(combined)
dev.off()

               