"""
# NOTAM Mapper
Generate interactive maps from notice to airman (NOTAM) documents
"""

import streamlit as st # Web app
import folium  # Display map
import pandas as pd  # Data manipulation
import re  # Text searching via regular expressions
from streamlit_folium import st_folium # Integrate maps with web apps

st.title('NOTAM Mapper')
st.write("Built with ☕ by [Johnathan Fernandes](johnathanfernandes.github.io/)")

rawtext = st.text_area("Paste NOTAM below:", height=400)

while len(rawtext)!=0: # User input check
    
    data = rawtext.replace("\n", " ")  # Join lines
    data = data.replace("  ", " ")  # Remove multiple spaces

    # Define text search terms
    circle_text = re.compile(
        r" E\)(.*?)(AREA CIRCLE WITH RADIUS) ([\d]*[\.][\d]*|[\d]*) (M|NM|KM) (CENTERED ON) (([0-9]*[\.][0-9]+)|([0-9]*))(N |S )(([0-9]*[\.][0-9]+)|([0-9]*))(W|E)"
    )
    poly_text = re.compile(
        r" E\)(.*?)(AREA BOUNDED BY LINES JOINING:((( [0-9]*[\.][0-9]+)|( [0-9]*))(N|S)(( [0-9]*[\.][0-9]+)|( [0-9]*))(W|E))*)"
    )

    # Search using regular expressions
    circles = pd.DataFrame(re.findall(circle_text, data))  # Circles
    polygons = pd.DataFrame(re.findall(poly_text, data))  # Polygons

    if (len(circles)+len(polygons) == 0):
        st.write("No events found. Exiting. Please raise an [issue on the github page](https://github.com/johnathanfernandes/NOTAM_mapper/issues) with your NOTAM")
        quit()

    def process_circles(circle):

        # Convert latitude from standard NOTAM notation to map form
        lat_deg = float(circle[5][0:2])
        lat_min = float(circle[5][2:4])
        lat_sec = float(circle[5][4:])
        lat = lat_deg + (lat_min / 60) + (lat_sec / 3600)

        # Convert longitude
        long_deg = float(circle[9][0:3])
        long_min = float(circle[9][3:5])
        long_sec = float(circle[9][5 : len(circle[9])])
        longi = long_deg + (long_min / 60) + (long_sec / 3600)

        # Convert NM and KM to M if present
        if circle[3] == "NM":
            rad = float(circle[2]) * 1852.001
        elif circle[3] == "KM":
            rad = float(circle[2]) * 1000
        else:
            rad = float(circle[2])

        # Define event name
        name = str(re.sub("(.*?)E\)", "", circle[0]) + " ".join(circle[1:]))

        return [name, lat, longi, rad]

    def process_polygons(polygon):

        # Keep only coordinate text
        coords_list = polygon[1][30:].split()
        coordinate_pairs = []

        # Iterate through coordinates and split into pairs
        for i in range(0, len(coords_list), 2):

            # Convert latitude
            lat_deg = float(coords_list[i][0:2])
            lat_min = float(coords_list[i][2:4])
            lat_sec = float(coords_list[i][4:-1])
            lat = lat_deg + (lat_min / 60) + (lat_sec / 3600)

            # Convert longitude
            long_deg = float(coords_list[i + 1][0:3])
            long_min = float(coords_list[i + 1][3:5])
            long_sec = float(coords_list[i + 1][5:-1])
            longi = long_deg + (long_min / 60) + (long_sec / 3600)

            coordinate_pairs.append([lat, longi])

        name = str(re.sub("(.*?)E\)", "", polygon[0]) + polygon[1])

        return [name, coordinate_pairs]

    if len(circles) != 0:
        circles.drop(circles.columns[[6, 7, 10, 11]], axis=1, inplace=True)
        circle_list = circles.apply(process_circles, axis=1, result_type="expand")
        circle_list.columns = ["Event name", "Latitude", "Longitude", "Radius (m)"]


    if len(polygons) != 0:
        polygons = polygons.iloc[:, 0:2]
        polygon_list = polygons.apply(process_polygons, axis=1, result_type="expand")
        polygon_list.columns = ["Event name", "Locations"]


    # Define mapping function
    def create_map():
        try:
            AIO_map = folium.Map(
                location=[
                    circle_list["Latitude"].median(),
                    circle_list["Longitude"].median(),
                ]
            )  # Try to center around median of circles
        except (ValueError,NameError):
            AIO_map = folium.Map(
                location=[
                    polygon_list["Locations"][0][1][
                        0
                    ],  # If no circles exist, center around first polygon
                    polygon_list["Locations"][0][1][1],
                ]
            )

        if len(circles) != 0:
            for idx, circle in circle_list.iterrows():
                folium.Circle(
                    location=(circle["Latitude"], circle["Longitude"]),
                    radius=circle["Radius (m)"],
                    popup=str(circle["Event name"]),
                    tooltip=str(circle["Event name"]),
                    fill=True,
                ).add_to(AIO_map)
                folium.Marker(
                    location=(circle["Latitude"], circle["Longitude"]),
                    icon=folium.features.DivIcon(
                        icon_size=(150, 36),
                        icon_anchor=(0, 0),
                        html='<div style="font-size: 12pt; background: rgba(0, 0, 0, .2)">%s</div>'
                        % circle["Event name"],
                    ),
                ).add_to(AIO_map)

        if len(polygons) != 0:
            for idx, polygon in polygon_list.iterrows():
                folium.Polygon(
                    locations=(polygon["Locations"]),
                    popup=str(polygon["Event name"]),
                    tooltip=str(polygon["Event name"]),
                    fill=True,
                ).add_to(AIO_map)
                folium.Marker(
                    location=(polygon["Locations"][0]),
                    icon=folium.features.DivIcon(
                        icon_size=(150, 36),
                        icon_anchor=(0, 0),
                        html='<div style="font-size: 12pt; background: rgba(0, 0, 0, .2)">%s</div>'
                        % polygon["Event name"],
                    ),
                ).add_to(AIO_map)

        return AIO_map

    AIO_map = create_map()

    st_image = st_folium(AIO_map,  width = 725)