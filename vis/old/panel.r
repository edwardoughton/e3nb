library(tidyverse)

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
                                         "25-40 km"))

plot1 = 
  ggplot(data, aes(received_power_db, frequency_category)) + coord_flip() +
  geom_boxplot() + geom_jitter(width = 0.5, size=.05, alpha=.2) +
  labs(title="(A) Simulation Results for the Received Signal based on the FSPL",
       colour=NULL,
       subtitle = "Reported for all frequency and distance categories",
       x = 'Received Signal (dB)', y = "Frequency (GHz)") +
  scale_x_continuous(expand = c(0, 0), limits = c(-40,0)) +
  facet_wrap(~distance_category)

############
folder <- dirname(rstudioapi::getSourceEditorContext()$path)
folder = file.path(folder, '..', 'data', 'intermediate', 'model_inputs')

filename = 'fresnel_clearances.csv'
data <- read.csv(file.path(folder, filename))

data = data[data$clearance > 1,]

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
  scale_x_continuous(expand = c(0, 0), limits = c(0,22.5)) +
  facet_wrap(~distance_category)

combined <- ggarrange(plot1, plot2,   
                      ncol = 1, nrow = 2)

folder <- dirname(rstudioapi::getSourceEditorContext()$path)
path = file.path(folder, 'figures', 'panel_plot.png')
ggsave(path, units="in", width=7, height=5, dpi=300)
print(combined)
dev.off()






# folder <- dirname(rstudioapi::getSourceEditorContext()$path)
# path = file.path(folder, 'figures', 'fresnel_clearances.png')
# ggsave(path, units="in", width=7, height=4, dpi=300)
# print(plot)
# dev.off()

