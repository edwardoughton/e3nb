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
         pop_d_decile = ntile(pop_density_km2, 10),)

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

plot1 = ggplot(data1, aes(x=pop_d_decile, y=cumulative_covered, 
                        colour=strategy, group=strategy)) +
  geom_line() +
  scale_fill_brewer(palette="Spectral", name = expression('Cost Type'), direction=1) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1), legend.position = "bottom") + 
  labs(title = "(A) Cumulative Population Reached by Population Decile", 
       colour=NULL,
       x = "Population Deciles", y = "Coverage (Millions)") +
  facet_wrap(~country, scales = "free", ncol=3)

plot2 = ggplot(data1, aes(x=pop_d_decile, y=cumulative_cost, 
                          colour=strategy, group=strategy)) +
  geom_line() +
  scale_fill_brewer(palette="Spectral", name = expression('Cost Type'), direction=1) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1), legend.position = "bottom") + 
  labs(title = "(B) Cumulative Investment Cost by Population Decile", 
       colour=NULL,
       # subtitle = "Reported for the percentage of population covered with 2 Mbps", 
       x = "Population Deciles", y = "Cost (Millions $USD)") +
  facet_wrap(~country, scales = "free", ncol=3)

combined <- ggarrange(plot1, plot2, 
                      ncol = 1, nrow = 2)

path = file.path(folder, 'figures', 'pop_decile_panel.png')
ggsave(path, units="in", width=7, height=7, dpi=300)
print(plot)
dev.off()


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

plot1 = ggplot(data2, aes(x=id_decile, y=cumulative_covered, 
                          colour=strategy, group=strategy)) +
  geom_line() +
  scale_fill_brewer(palette="Spectral", name = expression('Cost Type'), direction=1) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1), legend.position = "bottom") + 
  labs(title = "(A) Cumulative Population Reached by Terrain Decile", 
       colour=NULL,
       x = "Terrain Deciles", y = "Coverage (Millions)") +
  facet_wrap(~country, scales = "free", ncol=3)

plot2 = ggplot(data2, aes(x=id_decile, y=cumulative_cost, 
                          colour=strategy, group=strategy)) +
  geom_line() +
  scale_fill_brewer(palette="Spectral", name = expression('Cost Type'), direction=1) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1), legend.position = "bottom") + 
  labs(title = "(B) Cumulative Investment Cost by Terrain Decile", 
       colour=NULL,
       # subtitle = "Reported for the percentage of population covered with 2 Mbps", 
       x = "Terrain Deciles", y = "Cost (Millions $USD)") +
  facet_wrap(~country, scales = "free", ncol=3)

combined <- ggarrange(plot1, plot2, 
                      ncol = 1, nrow = 2)

path = file.path(folder, 'figures', 'id_range_panel.png')
ggsave(path, units="in", width=7, height=7, dpi=300)
print(plot)
dev.off()
