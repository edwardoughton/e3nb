e3nb
====

Engineering-Economic Evaluation of Non-Line-of-Sight Backhaul (e3nb)

**e3nb** enables the economic costs of Non-Line-of-Sight (NLOS) backhaul to be quantified.

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

Once all necessary processing has been carried out, the main run script can be executed:

    python scripts/run.py


Thanks for the support
======================

**e3nb** was written and developed at `George Mason University <https://www2.gmu.edu/>`.
