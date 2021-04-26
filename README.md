Engineering-Economic Evaluation of Non-Line-of-Sight Backhaul (e3nb)
====

**e3nb** is a techno-economic simulation model for 3D wireless backhaul assessment.

The codebase enables the investment requirements of Clear-Line-Of-Sight and diffractive
Non-Line-Of-Sight (NLOS) wireless backhaul to be quantified using three-dimensional (3D)
viewshed methods.

Figure 1 provides an example of the two deployment situations for CLOS and diffractive
NLOS.

## Figure 1 - Example of Clear-Line-Of-Sight versus diffractive Non-Line-Of-Sight links

<p align="center">
  <img src="/figures/clos_vs_nlos.png" />
</p>

Using the **e3nb** codebase, different 3D wireless link strategies can be compared.
For example, when deploying only Clear-Line-Of-Sight wireless links, the generalized
flow diagram illustrated in Figure 2 represents a standardized approach.

## Figure 2 Flow diagram for deployment of Clear-Line-Of-Sight links

<p align="center">
  <img src="/figures/clos_flow.png" />
</p>

Equally, as more Mobile Network Operators move to deploy diffractive Non-Line-Of-Sight
links in their networks, the generalized flow diagram illustrated in Figure 3 represents
the type of high-level network planning evaluation that is required as a first step,
before undertaking detailed Quality of Service (QoS) Radio Frequency (RF) engineering.

## Figure 3 Flow diagram for deployment of Non-Line-Of-Sight links

<p align="center">
  <img src="/figures/nlos_flow.png" />
</p>

Once the **e3nb** codebase has been fully executed, an example of the types of
comparative network designs that can be produced is shown in Figure 4. The modeling
region shown is for an area of northern Peru containing the city of Chachapoyas (~30k inhabitants), which is surrounded by many smaller unconnected settlements ranging from 5,000 down to only 250 inhabitants.

## Figure 4 Illustration of network designs based on different wireless strategies

<p align="center">
  <img src="/figures/network_plot.png" />
</p>

The types of results the codebase produces are visualized in Figure 5, for two islands
in Indonesia (Kalimantan and Papua), as well as for Peru. The results are reported based
on population density or terrain irregularity deciles. Importantly, deploying diffractive
Non-Line-Of-Sight (NLOS) wireless backhaul links provide a cost efficiency saving ranging
from 15-43%. This saving can be reinvested into connecting more people to broadband
services.

## Figure 5 Cumulative cost results for Indonesia and Peru

<p align="center">
  <img src="/figures/results_panel.png" />
</p>

Using conda
==========

The recommended installation method is to use conda, which handles packages and virtual
environments, along with the conda-forge channel which has a host of pre-built libraries and
packages.

Create a conda environment called e3nb:

    conda create --name e3nb python=3.7 gdal

Activate it (run this each time you switch projects):

    conda activate e3nb

First, install optional packages:

    conda install geopandas

Then install e3nb:

    python setup.py install

Alternatively, for development purposes, clone this repo and run:

    python setup.py develop


Quick start
===========

To prepare the data for running the model, first you need to execute:

    python scripts/prep.py

As well as running the Line-Of-Sight assessment script:

    python scripts/los.py

Once all necessary processing has been carried out, the main run script can be executed:

    python scripts/run.py

And the results can be collected and disaggregated:

    python scripts/disaggregate.py


Thanks for the support
======================

**e3nb** was written and developed at `George Mason University <https://www2.gmu.edu/>`.
