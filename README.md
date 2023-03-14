# Slicing Simulator Project

## Overview
This project is part of a networking course and showcases a simulation a network slicing.

The goal of this implementation is to test different ressource reallocation policies and compare the results.

## The simulation
We consider 1 base antenna divided into 2 virtual slices, each with their specified quality of service.

General parameters:
- Number of slices : 2
- Simulation time : 60 seconds
- Central Capacity : 20
- Re-slicing time: $\frac{simulation\_time}{10}$

|Slice 1|Slice 2|
|----|----|
|Rmin = 0.1|Rmin = 1|
|Rmax = 7|Rmax = 1.5|
|$\gamma = 0.3$|$\gamma =0.7$|
|$\lambda_{adist} = 2$|$\lambda_{adist} = 1$|
|$\lambda_{sdist} = 35$|$\lambda_{sdist} = 1$|

We implemented two slicing schemes :
- Static : Allocate a fix resource from the start.
- Timed Re-slicing : Reallocate periodically using a timer.

They are respectively assigned to 0 and 1 in the __<type_of_reclicing_trigger>__ argument found in the following section.

## How to run the code
- Clone the Repository 
- Install the required dependecies with :
  ```
  pip install -r ./requirements.txt
  ```
- Then simply run the __Slicing_simulation.py__ file in __./src__ as such :
    ```
    python3 Sclicing_simulation.py <simulation_time> <type_of_reclicing_trigger>
    ```

## Report

For more information refer to the __report.pdf__ in the __/docs__ folder.