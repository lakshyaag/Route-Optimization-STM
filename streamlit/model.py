import numpy as np
import pandas as pd
import streamlit as st
import gurobipy as gb

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import geopandas as gpd
from shapely.geometry import Point, LineString
import split


def define_model(
    stops: list,
    buses: int,
    demand: dict,
    distance_matrix: pd.DataFrame,
    BUS_CAPACITY: int,
    DISTANCE_THRESHOLD: float = 5.0,
    **params,
):
    # ----------------------------------------------------------------------------------------------
    # Model

    model = gb.Model("Bus Routing")
    model.Params.MIPGap = params.get("MIPGap", 0.05)
    model.Params.TimeLimit = params.get("TimeLimit", 60 * 3)
    model.Params.MIPFocus = params.get("MIPFocus", 1)
    model.Params.LogToConsole = params.get("LogToConsole", 1)

    # ----------------------------------------------------------------------------------------------
    # Decision Variables

    x = model.addVars(
        stops,
        stops,
        buses,
        vtype=gb.GRB.BINARY,
        name=(
            f"{i} -> {j} (bus {k})" for i in stops for j in stops for k in range(buses)
        ),
    )

    u = model.addVars(
        stops,
        vtype=gb.GRB.INTEGER,
        name=(f"Load at Stop {i}" for i in stops),
    )

    # ----------------------------------------------------------------------------------------------
    # Objective Function
    model.setObjective(
        gb.quicksum(
            distance_matrix.loc[i, j] * x[i, j, k]
            for i in stops
            for j in stops
            for k in range(buses)
        ),
        gb.GRB.MINIMIZE,
    )

    # ----------------------------------------------------------------------------------------------
    # Constraints

    # Vehicle leaves nodes that it enters
    model.addConstrs(
        (
            gb.quicksum(x[j, i, k] for j in stops)
            == gb.quicksum(x[i, j, k] for j in stops)
            for i in stops
            for k in range(buses)
        ),
        name="Vehicle leaves nodes that it enters",
    )

    # Every node is entered once
    model.addConstrs(
        (
            gb.quicksum(x[i, j, k] for i in stops for k in range(buses)) == 1
            for j in stops[1:]
        ),
        name="Every node is entered once",
    )

    # Every vehicle leaves the depot
    model.addConstrs(
        (gb.quicksum(x[stops[0], j, k] for j in stops[1:]) <= 1 for k in range(buses)),
        name="Every vehicle may leave the depot if needed",
    )

    # Capacity constraint
    model.addConstrs(
        (
            gb.quicksum(demand[j] * x[i, j, k] for j in stops[1:] for i in stops)
            <= BUS_CAPACITY
            for k in range(buses)
        ),
        name="Capacity constraint",
    )

    # No travel between same node
    model.addConstrs(
        (x[i, i, k] == 0 for i in stops for k in range(buses)),
        name="No same node",
    )

    # Subtour elimination constraints
    model.addConstrs(
        (
            u[j] - u[i] >= demand[j] - BUS_CAPACITY * (1 - x[i, j, k])
            for i in stops[1:]
            for j in stops[1:]
            for k in range(buses)
            if i != j
        ),
        name="Subtour elimination constraint",
    )

    model.addConstrs(
        (u[i] >= demand[i] for i in stops[1:]),
        name="Lower bound for u",
    )

    model.addConstrs(
        (u[i] <= BUS_CAPACITY for i in stops[1:]),
        name="Upper bound for u",
    )

    # Distance between two travel nodes is less than specified distance
    model.addConstrs(
        (
            distance_matrix.loc[i, j] * x[i, j, k] <= DISTANCE_THRESHOLD
            for i in stops[1:]
            for j in stops[1:]
            for k in range(buses)
        ),
        name="Distance between two travel nodes is less than a specified distance",
    )

    # ----------------------------------------------------------------------------------------------
    # Solve model
    model._vars = x
    model.update()

    return model


def solve_model(
    depot,
    stops_df,
    distance_matrix,
    num_buses,
    stops_in_disaster_area,
    BUS_CAPACITY,
    DEMAND_LIMIT: int = 100,
    DISTANCE_THRESHOLD: float = 5.0,
    split_type: str = "geometric",
    MIPGap: float = 0.2,
    TimeLimit: int = 60 * 3,
    MIPFocus: int = 1,
    LogToConsole: int = 1,
):
    rng = np.random.default_rng(5)

    distance_matrix_model = distance_matrix.drop(
        columns=stops_in_disaster_area.stop_id, index=stops_in_disaster_area.stop_id
    )

    stops = list(distance_matrix_model.columns)
    num_stops = len(stops)

    distance_matrix_model = distance_matrix_model.loc[stops, stops]

    demand = {stop: rng.integers(1, DEMAND_LIMIT) for stop in stops}
    demand[stops[0]] = 0

    st.markdown(f"`Total demand: {sum(demand.values())}`")
    st.markdown(f"`Total capacity: {num_buses * BUS_CAPACITY}`")

    new_demand, nodes_exceeding_demand = split.reconstruct_demand(
        demand, BUS_CAPACITY, rng, split_type
    )

    distance_matrix_model_pruned = split.update_distance_matrix(
        distance_matrix_model, nodes_exceeding_demand, new_demand
    )

    for k, v in new_demand.items():
        assert v <= BUS_CAPACITY

    assert sum(new_demand.values()) == sum(demand.values())

    new_stops = list(distance_matrix_model_pruned.columns)
    num_new_stops = len(new_stops)

    st.markdown(f"`Total number of stops: {num_stops}`")
    st.markdown(
        f"`Total number of new stops (including splits of type = {split_type}): {num_new_stops}`"
    )

    model = define_model(
        new_stops,
        num_buses,
        new_demand,
        distance_matrix_model_pruned,
        BUS_CAPACITY,
        DISTANCE_THRESHOLD,
        MIPGap=MIPGap,
        TimeLimit=TimeLimit,
        MIPFocus=MIPFocus,
        LogToConsole=LogToConsole,
    )

    model.optimize()

    distance_bus, bus_path_df, paths = show_solution(
        model,
        new_stops,
        num_buses,
        new_demand,
        nodes_exceeding_demand,
        distance_matrix_model_pruned,
        stops_df,
    )

    network_plots = plot_networkx_bus(bus_path_df)
    st.write(network_plots)

    routes_gdf = build_route_df(bus_path_df, depot)

    # route_map = plot_routes(
    #     distance_matrix, bus_path_df, routes_gdf, num_buses, split_type
    # )

    return {
        "split_type": split_type,
        "demand": demand,
        "new_demand": new_demand,
        "model": model,
        "distance_bus": distance_bus,
        "bus_path_df": bus_path_df,
        "paths": paths,
        "network_plots": network_plots,
        "routes_gdf": routes_gdf,
        # "route_map": route_map,
    }


def show_solution(
    model, stops, buses, demand, nodes_exceeding_demand, distance_matrix, stops_df
):
    x = model._vars

    print("-" * 100)
    print(f"Objective value: {model.objVal:.2f} km")
    print("-" * 100)

    # Distance by bus
    distance_bus = pd.DataFrame(
        {
            "bus": k,
            "distance": sum(
                distance_matrix.loc[i, j] * x[i, j, k].x for i in stops for j in stops
            ),
        }
        for k in range(buses)
    )

    distance_bus = distance_bus[distance_bus["distance"] > 0].reset_index(drop=True)

    # display(distance_bus)

    # Bus paths
    bus_path = {}

    for k in range(buses):
        bus_path[k] = []
        for i in stops:
            for j in stops:
                if x[i, j, k].x == 1:
                    bus_path[k].append(
                        {
                            "start_stop": i,
                            "end_stop": j,
                            "distance": distance_matrix.loc[i, j],
                        }
                    )

    # Convert to dataframe with bus route number
    bus_path_df = []

    for k, v in bus_path.items():
        bus_path_df.append(pd.DataFrame(v).assign(bus=k))

    bus_path_df = pd.concat(bus_path_df)

    paths = {}

    grouped = bus_path_df.groupby("bus")

    # Iterate over each bus group
    for bus, group in grouped:
        sorted_group = group.sort_values(by=["start_stop", "end_stop"]).reset_index(
            drop=True
        )
        path = ["0"]  # Initialize the path with the depot

        # Start with the first stop after the depot
        current_stop = sorted_group.loc[
            sorted_group["start_stop"] == "0", "end_stop"
        ].values[0]
        path.append(current_stop)

        # Follow the chain of stops
        while True:
            # Find the next stop where the current stop is the start stop
            next_stop = sorted_group.loc[
                sorted_group["start_stop"] == current_stop, "end_stop"
            ].values
            if not next_stop:
                break  # If there is no next stop, we've completed the path
            next_stop = next_stop[0]

            # Add the next stop to the path and set it as the current stop
            if next_stop == "0":
                break  # If the next stop is the depot, we've completed the path
            path.append(next_stop)
            current_stop = next_stop

        # Store the path for this bus
        paths[bus] = path

    bus_path_df["step"] = bus_path_df.apply(
        lambda x: paths[x.bus].index(x.start_stop), axis=1
    )

    bus_path_df.sort_values(by=["bus", "step"], inplace=True)

    bus_path_df["demand"] = bus_path_df["end_stop"].map(demand)

    bus_path_df[["start_stop", "end_stop"]] = bus_path_df[
        ["start_stop", "end_stop"]
    ].applymap(lambda x: x.split("_")[0])

    bus_path_df = bus_path_df.merge(
        stops_df[["stop_id", "stop_name", "geometry"]],
        left_on="end_stop",
        right_on="stop_id",
        how="left",
    )

    bus_path_df["step_demand"] = bus_path_df.groupby("bus")["demand"].cumsum()

    bus_path_df["is_split"] = bus_path_df["stop_id"].isin(nodes_exceeding_demand.keys())

    num_buses_used = bus_path_df.bus.nunique()
    print(f"Number of buses used: {num_buses_used}")

    # display(bus_path_df)

    # Print routes
    # for route in paths:
    #     print(f"Bus {route}: {' -> '.join(paths[route])} -> 0")

    return distance_bus, bus_path_df, paths


def plot_networkx_bus(bus_path_df):
    plots = {}
    for bus in bus_path_df.bus.unique():
        # print(f"Bus {bus + 1}:")

        bus_route = bus_path_df[bus_path_df["bus"] == bus].reset_index(drop=True)

        fig = plt.figure(figsize=(20, 10))

        g = nx.DiGraph()

        for segment in bus_route.itertuples():
            g.add_edge(
                segment.start_stop,
                segment.end_stop,
                weight=segment.distance,
                step=segment.step,
                demands={"demand": segment.demand, "load": segment.step_demand},
                label=f"{segment.start_stop}-{segment.end_stop}",
            )

        pos = nx.circular_layout(g)

        nx.draw_networkx(g, pos, with_labels=True, node_size=500, node_color="skyblue")
        nx.draw_networkx_edge_labels(
            g, pos, edge_labels=nx.get_edge_attributes(g, "demands")
        )

        plots[bus] = fig

    plt.close("all")
    return plots


def build_route_df(bus_path_df, depot):
    routes_gdf = (
        gpd.GeoDataFrame(bus_path_df.groupby("bus")["geometry"].apply(list))
        .rename(columns={"points": "geometry"})
        .reset_index()
    )

    # add depot to each geometry
    routes_gdf["points"] = routes_gdf.apply(
        lambda x: [Point((float(depot.stop_lon), float(depot.stop_lat)))] + x.geometry,
        axis=1,
    )

    routes_gdf["geometry"] = routes_gdf["points"].apply(LineString)
    routes_gdf.drop(columns=["points"], inplace=True)

    routes_gdf = routes_gdf.merge(
        bus_path_df.groupby("bus")["demand"].sum().rename("demand").reset_index(),
        on="bus",
    )

    routes_gdf = gpd.GeoDataFrame(routes_gdf, geometry="geometry")
    routes_gdf.crs = "EPSG:4326"

    # display(routes_gdf)

    return routes_gdf
