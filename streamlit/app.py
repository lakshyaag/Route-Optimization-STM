import os

import load
import maps
import model
import pandas as pd
from streamlit_folium import folium_static, st_folium

import streamlit as st

# Session state
if "depot_location" not in st.session_state:
    st.session_state.depot_location = None

if "disaster_area" not in st.session_state:
    st.session_state.disaster_area = None

if "model_solved" not in st.session_state:
    st.session_state.model_solved = False

if "model_" not in st.session_state:
    st.session_state.model_solved = None

# Page configuration
st.set_page_config(page_title="MGSC 662 - Route Optimization Model", layout="wide")

st.sidebar.markdown("# Parameters")
# Use sliders, number inputs, etc., to get user input
with st.sidebar:
    st.markdown("### Model parameters")
    NUM_STOPS = st.number_input("Number of Stops", min_value=10, max_value=40, value=15)
    NUM_BUSES = st.number_input("Number of Buses", min_value=1, value=15)
    BUS_CAPACITY = st.number_input("Bus Capacity", min_value=1, value=80)
    DEMAND_LIMIT = st.number_input("Demand Limit", min_value=1, value=120)
    DISTANCE_THRESHOLD = st.slider(
        "Distance threshold (in kms)", min_value=1, max_value=10, value=5
    )
    SPLIT_TYPE = st.selectbox(
        "Split Type",
        ["geometric", "capacity", "random"],
        0,
        format_func=lambda x: x.lower().capitalize(),
    )

    st.markdown("### Solver parameters")
    TIME_LIMIT = st.slider(
        "Time Limit (in seconds)", min_value=60, max_value=900, value=180
    )
    MIP_GAP = st.slider("MIP Gap", min_value=0.01, max_value=1.0, value=0.1, step=0.05)
    LOG_TO_CONSOLE = st.selectbox(
        "Log to Console", [0, 1], 1, format_func=lambda x: "Yes" if x == 1 else "No"
    )


st.title("Route Optimization Model")

stops_file = "./stops.csv"
segments_file = "./segments.csv"

IS_DATA_LOADED = False


if os.path.exists(stops_file) and os.path.exists(segments_file):
    # Load data
    stops_df = pd.read_csv(stops_file)
    segments_df = pd.read_csv(segments_file)

    segments_df[["route_id", "start_stop_id", "end_stop_id"]] = segments_df[
        ["route_id", "start_stop_id", "end_stop_id"]
    ].astype(str)

    IS_DATA_LOADED = True

else:
    st.error("File path(s) not found. Please check the file paths.")


if IS_DATA_LOADED:
    route_list = ["24", "51", "67", "18", "105", "45", "80", "55"]

    stops_df_gpd = load.get_stops_on_route(route_list, segments_df, stops_df)

    random_stops_df_gpd = load.get_random_stops(stops_df_gpd, NUM_STOPS, 662)

    col1, col2 = st.columns(2)

    with col1:
        # Add depot
        with st.expander("**Add a depot location**"):
            add_depot = st.button(
                "Add depot", use_container_width=True, key="add_depot", type="primary"
            )

            m = maps.add_depot_map(random_stops_df_gpd)
            depot_location = st_folium(
                m,
                key="depot_map",
                width=1000,
                height=500,
                returned_objects=["all_drawings"],
            )

            if add_depot:
                if depot_location.get("all_drawings") is not None:
                    st.session_state["depot_location"] = depot_location["all_drawings"][
                        0
                    ]["geometry"]["coordinates"]

    with col2:
        if st.session_state["depot_location"] is not None:
            depot_lon, depot_lat = st.session_state["depot_location"]

            depot, random_stops_df_gpd = load.add_depot(
                depot_lat, depot_lon, random_stops_df_gpd
            )

            with st.spinner(
                "Loading distance matrix...",
            ):
                distance_matrix = load.get_distance_matrix(random_stops_df_gpd)

            with st.expander("**Add a disaster area**"):
                add_disaster_area = st.button(
                    "Add disaster area",
                    use_container_width=True,
                    key="add_disaster_area",
                    type="primary",
                )

                m = maps.add_disaster_area(random_stops_df_gpd)

                disaster_area = st_folium(
                    m,
                    key="disaster_map",
                    width=1000,
                    height=500,
                    returned_objects=["all_drawings"],
                )

                if add_disaster_area:
                    if disaster_area.get("all_drawings") is not None:
                        st.session_state["disaster_area"] = disaster_area[
                            "all_drawings"
                        ][0]["geometry"]["coordinates"]

    if st.session_state["disaster_area"] is not None:
        disaster_bounds = st.session_state["disaster_area"][0]

        stops_in_disaster_area, disaster_area = load.add_disaster_area(
            random_stops_df_gpd, [*disaster_bounds[0], *disaster_bounds[2]]
        )

        with st.expander("**Show unsolved network**"):
            st.markdown(f"`Number of stops in sample: {len(random_stops_df_gpd)}`")
            st.markdown(
                f"`Number of stops in disaster area: {len(stops_in_disaster_area)}`"
            )

            folium_static(
                maps.show_unsolved_network(
                    random_stops_df_gpd,
                    disaster_area,
                    stops_in_disaster_area,
                    distance_matrix,
                ),
                width=1000,
                height=600,
            )

    if (
        st.session_state["depot_location"] is not None
        and st.session_state["disaster_area"] is not None
    ):
        with st.expander("**Solve model**"):
            solve_model = st.button(
                "Solve model", type="primary", use_container_width=True
            )

            if solve_model:
                with st.spinner("Solving model..."):
                    model_ = model.solve_model(
                        depot,
                        random_stops_df_gpd,
                        distance_matrix,
                        NUM_BUSES,
                        disaster_area,
                        stops_in_disaster_area,
                        BUS_CAPACITY,
                        DEMAND_LIMIT,
                        DISTANCE_THRESHOLD,
                        SPLIT_TYPE,
                        MIP_GAP,
                        TIME_LIMIT,
                        LOG_TO_CONSOLE,
                    )

                    st.session_state["model_solved"] = True
                    st.session_state["model_"] = model_

        if st.session_state["model_solved"]:
            model_ = st.session_state["model_"]
            with st.expander("**Show solved network**"):
                st.markdown(
                    f"`Total distance travelled: {model_['model'].objVal:.2f} kms`"
                )

                st.markdown(
                    f"`Number of buses used: {model_['bus_path_df'].bus.nunique()}`"
                )

                st.markdown("#### **Optimal route map**")
                folium_static(
                    model_["route_map"],
                    width=1000,
                    height=500,
                )

                st.markdown("#### **Routes**")
                for path, route in model_["paths"].items():
                    stop_names = random_stops_df_gpd[
                        random_stops_df_gpd["stop_id"].isin(
                            [r.split("_")[0] for r in route]
                        )
                    ].loc[:, "stop_name"]

                    stop_names_split = [r.find("_") for r in route]

                    if len(stop_names) > 1:
                        final_stop_names = [
                            s + " (SPLIT)" if v > -1 else s
                            for s, v in dict(zip(stop_names, stop_names_split)).items()
                        ]

                        st.markdown(
                            f"`Route {path}: {' >> '.join(final_stop_names)} >> Depot`"
                        )
                    else:
                        st.write(route)
