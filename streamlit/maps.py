import folium
from folium.plugins import Draw


def add_depot_map(stops_df):
    m = folium.Map(
        location=[45.5048542, -73.5691235],
        zoom_start=11,
        tiles="cartodbpositron",
        width="100%",
    )

    for stop in stops_df.itertuples():
        folium.CircleMarker(
            location=[stop.stop_lat, stop.stop_lon],
            radius=3,
            color="darkgreen",
            fill=True,
            fill_opacity=1,
            fill_color="darkgreen",
            tooltip=f"{stop.stop_name} ({stop.stop_id})",
            popup=f"""
            <div>
                <h4>{stop.stop_name} ({stop.stop_id})</h4>
            </div>
            """,
        ).add_to(m)

    # Add drawing tool to the map
    draw = Draw(
        draw_options={
            "polyline": False,
            "rectangle": False,
            "circle": False,
            "marker": True,
            "circlemarker": False,
            "polygon": False,
        }
    )
    draw.add_to(m)

    return m


def add_disaster_area(stops_df):
    m = folium.Map(
        location=[45.5048542, -73.5691235],
        zoom_start=11,
        tiles="cartodbpositron",
        width="100%",
    )

    for stop in stops_df.itertuples():
        folium.CircleMarker(
            location=[stop.stop_lat, stop.stop_lon],
            radius=3,
            color="darkgreen" if stop.stop_id != "0" else "blue",
            fill=True,
            fill_opacity=1,
            fill_color="darkgreen" if stop.stop_id != "0" else "blue",
            tooltip=f"{stop.stop_name} ({stop.stop_id})",
            popup=f"""
            <div>
                <h4>{stop.stop_name} ({stop.stop_id})</h4>
            </div>
            """,
        ).add_to(m)

    # Add drawing tool to the map
    draw = Draw(
        draw_options={
            "polyline": False,
            "rectangle": True,
            "circle": False,
            "marker": True,
            "circlemarker": False,
            "polygon": False,
        }
    )
    draw.add_to(m)

    return m


def show_unsolved_network(
    stops_df, disaster_area, stops_in_disaster_area, distance_matrix
):
    m = folium.Map(
        location=[45.5048542, -73.5691235],
        zoom_start=11,
        tiles="cartodbpositron",
        width="100%",
    )

    # Add disaster area
    folium.GeoJson(
        disaster_area,
        name="Disaster area",
        style_function=lambda x: {
            "color": "#ff0000",
            "fillColor": "#ff0000",
            "weight": 1,
            "fillOpacity": 0.4,
        },
    ).add_to(m)

    for stop in stops_df.itertuples():
        folium.CircleMarker(
            location=[stop.stop_lat, stop.stop_lon],
            radius=3,
            color=(
                "red"
                if stop.stop_id in stops_in_disaster_area.stop_id.values.tolist()
                else "darkgreen"
                if stop.stop_id != "0"
                else "blue"
            ),
            fill=True,
            fill_opacity=1,
            fill_color=(
                "red"
                if stop.stop_id in stops_in_disaster_area.stop_id.values.tolist()
                else "darkgreen"
                if stop.stop_id != "0"
                else "blue"
            ),
            tooltip=f"{stop.stop_name} ({stop.stop_id})",
            popup=f"""
            <div>
                <h4>{stop.stop_name} ({stop.stop_id})</h4>
                <h4>Distance from depot: {distance_matrix.loc["0", stop.stop_id]:.1f} km</h4>
            </div>
            """,
        ).add_to(m)

    folium.plugins.Fullscreen(position="topright").add_to(m)
    folium.plugins.MousePosition(position="topright").add_to(m)

    return m
