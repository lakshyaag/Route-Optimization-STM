# MGSC 662 - Decision Analytics - Project

This repository contains the code and data for the final project for MGSC 662 - Decision Analytics. The final project is a part of the course curriculum for the Master of Management in Analytics (MMA) program at the Desautels Faculty of Management, McGill University.

## Report

The report for the project can be found [here](./deliverables/MGSC_662-Final_Project_Report-Group_3.pdf).

## How to run

We present 2 ways to run the optimization model:

### Jupyter Notebook

1. Run the first cell to install all the necessary packages
2. Choose the bus routes to consider, the number of stops, the depot location, and the disaster area by changing these variables:
   - `routes`: list of bus routes to consider
   - `NUM_STOPS`: number of stops to consider
   - `depot`: depot location in `add_depot` (lat, lon)
   - `disaster_area`: disaster area in `add_disaster_area` (lat1, lon1, lat2, lon2)
3. Run all cells to load the necessary functions to run the optimization model (till "Run this model" section)
4. Choose the model parameters such as `NUM_BUSES`, `BUS_CAPACITY`, `DEMAND_LIMIT`, `DISTANCE_THRESHOLD` and solver parameters such as `TIME_LIMIT` and `MIPGap`
5. Run the specific type of model by choosing `split_type` among `geometric`, `capacity`, `random`, and `equal`
6. Call the `view_model` on the output of the above execution to see the model and the results

### Streamlit Application

1. Run `pip install -r requirements.txt` to install all the necessary packages
2. Run `streamlit run streamlit/app.py` to run the app
3. Add a depot location, wait for the distance matrix to be calculated, and then add a disaster area
4. Choose the model and solver parameters and run the model
