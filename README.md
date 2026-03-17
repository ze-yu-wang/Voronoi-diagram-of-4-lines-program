# Search engine for the Voronoi diagram of four lines in $R^3$

Code accompanying the paper:

**The Voronoi Diagram of Four Lines in $\mathbb{R}^3$** 
*Evanthia Papadopoulou, Zeyu Wang*

Accepted at the **42nd International Symposium on Computational Geometry (SoCG 2026)**  
Full version available on **[arXiv](https://arxiv.org/abs/[identifier])**


----

## Overview

This file contains the program we use for the exhaustive search algorithm to find all realizable 6-tuples of configurations associated with the Voronoi diagram of four lines. 

### File explanation

- `simple_configurations.pdf` contains all simple configurations (configurations with no twists).
- `trimodel.py` is a module containing all data structures and functions that are used in the search. In particular, it models trisector branches, trisectors, bisector configurations in their own classes and provide the main search function `get_valid_comb()` to obtain valid (those that survive all filters) configuration tuples. 

### How to run the program? 

We break the search into different cases to reduce the search space. We distinguish by the number Voronoi vertices and the number of induced vertices of each trisector in $\Gamma(NVD(L))$. For each subcase, go to the respective folder and run the notebook by loading the configuration data and then run `get_valid_comb`. 

### How to recover a configuration from its name? 

For the input configurations, see the folders `configsxxxx`. Each file starts with the form `k_ab`, where $k$ is the number of Voronoi vertices and the bisector configuration is an $(a,b)$-bisector.

Those files that end with `_no.yaml` are simple configurations (with no twists), those without any flags are all configurations, and those that end with `_short.yaml` contain all configurations without repetition (obtained from the previous list by merging repetitions). 

If a configuration's name is of the form `Configabc`, then it is a simple configuration and one directly goes to `simple_configurations.pdf` to find it. Otherwise, it is of the form `Configabc_l`, which means that it is the $l$-th configuration obtained from the simple configuration `Configabc` by adding twists. Go to the corresponding `k_ab.yaml` file for a description that shows where the twists are. 
