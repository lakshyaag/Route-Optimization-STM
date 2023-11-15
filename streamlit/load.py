import os
import streamlit as st
import numpy as np
import pandas as pd
from shapely.geometry import Point, box
import geopandas as gpd

import osmnx as ox
import networkx as nx


@st.cache_data
# Get segment and stops on route
def get_segment_stops(
    segment_df: pd.DataFrame,
    stops_df: pd.DataFrame,
    route_id: str,
    direction_id: int = 0,
):
    segment_distance = segment_df.query(
        "route_id == @route_id & direction_id == @direction_id"
    )

    stops_in_route = stops_df[
        stops_df["stop_id"].isin(
            list(
                set(
                    segment_distance[["start_stop_id", "end_stop_id"]].values.reshape(
                        -1
                    )
                )
            )
        )
    ]

    return segment_distance, stops_in_route


@st.cache_data
# Get unique stops on route
def get_stops_on_route(
    route_ids: list, segment_df: pd.DataFrame, stops_df: pd.DataFrame
):
    route_details = {}

    for r in route_ids:
        detail = get_segment_stops(segment_df, stops_df, r, 0)

        route_details[r] = {}
        route_details[r]["segment"] = detail[0]
        route_details[r]["stops"] = detail[1]

    stops_df = pd.concat(
        [v["stops"] for k, v in route_details.items()]
    ).drop_duplicates()

    print(f"Number of total stops in routes: {len(stops_df)}")

    stops_df["geometry"] = stops_df.apply(
        lambda x: Point((float(x.stop_lon), float(x.stop_lat))), axis=1
    )

    stops_df_gpd = gpd.GeoDataFrame(
        stops_df.drop(
            columns=["location_type", "parent_station", "wheelchair_boarding"]
        ),
        geometry="geometry",
    )

    print(stops_df_gpd.head())

    return stops_df_gpd


def get_random_stops(stops_df_gpd, n=20, random_state=5):
    return stops_df_gpd.sample(n=n, random_state=random_state)


def add_depot(lat: float, lon: float, stops_df: pd.DataFrame):
    depot = pd.DataFrame(
        {
            "stop_id": ["0"],
            "stop_name": ["Depot"],
            "stop_lat": [lat],
            "stop_lon": [lon],
            "stop_code": 0.0,
        }
    )

    depot["geometry"] = Point((float(depot.stop_lon), float(depot.stop_lat)))

    stops_df_gpd = pd.concat([depot, stops_df]).reset_index(drop=True)

    return depot, stops_df_gpd


def add_disaster_area(stops_df: pd.DataFrame, disaster_bounds: list):
    disaster_area = box(*disaster_bounds)

    stops_df_gpd = gpd.GeoDataFrame(stops_df, geometry="geometry")

    stops_in_disaster_area = stops_df_gpd[stops_df_gpd.within(disaster_area)]

    return stops_in_disaster_area, disaster_area


@st.cache_data
def get_distance_matrix(stops_df: pd.DataFrame):
    if os.path.exists("./distance_matrix.json"):
        print("Loading distance matrix from JSON")
        distance_matrix = pd.read_json("distance_matrix.json")

        distance_matrix.columns = distance_matrix.columns.astype(str)
        distance_matrix.index = distance_matrix.index.astype(str)

        return distance_matrix

    G = ox.load_graphml("montreal_drive.graphml")

    distance_matrix = np.zeros((len(stops_df), len(stops_df)))

    for i, stop1 in enumerate(stops_df.itertuples()):
        print(f"Calculating distance for stop {i}")
        for j in range(i + 1, len(stops_df)):
            stop2 = stops_df.iloc[j]

            origin = ox.nearest_nodes(G, stop1.stop_lon, stop1.stop_lat)
            destination = ox.nearest_nodes(G, stop2.stop_lon, stop2.stop_lat)

            try:
                distance = nx.shortest_path_length(
                    G, origin, destination, weight="length"
                )
            except nx.NetworkXNoPath:
                distance = np.Inf

            distance_matrix[i, j] = distance
            distance_matrix[j, i] = distance

        print("-" * 50)

    # Convert to km and save as JSON
    distance_matrix = pd.DataFrame(
        distance_matrix / 1000,
        columns=stops_df.stop_id,
        index=stops_df.stop_id,
    )

    distance_matrix.to_json("distance_matrix.json")

    return distance_matrix
