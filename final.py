import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
import plotly.express as px
import time
import random
from PIL import Image
from fpdf import FPDF
from twilio.rest import Client
import googlemaps

# Twilio API Credentials


# Google Maps API K

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
GMAPS_API_KEY = os.getenv("GMAPS_API_KEY")
gmaps = googlemaps.Client(key=GMAPS_API_KEY)
# Initialize Twilio client
from twilio.rest import Client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Load UI assets
logo = Image.open("dustbin_logo.jpg")
header_img = Image.open("header.jpg")

# Streamlit UI Config
st.title("Welcome to the AI-model of Dustbin")

st.image(header_img, use_column_width=True)
st.sidebar.image(logo, width=200)
st.sidebar.title("MCD Admin Panel")

user_role = st.sidebar.radio("Select Role", ["Admin", "Field Worker"])


# Generate real-time bin data
def generate_bin_data():
    bins = []
    for i in range(10):
        bins.append({
            "Bin ID": f"Bin-{i + 1}",
            "Latitude": random.uniform(28.5, 28.9),
            "Longitude": random.uniform(77.0, 77.5),
            "Fill Level (%)": random.randint(20, 100),
            "Temperature (°C)": random.uniform(20, 40),
            "Humidity (%)": random.uniform(30, 80),
            "Tilt": random.choice([0, 1]),
            "Tilt Alert": random.choice([True, False]),
            "Last Updated": time.strftime('%Y-%m-%d %H:%M:%S')
        })
    return pd.DataFrame(bins)


# Compute priority for bin collection
def calculate_priority(df):
    df["Priority"] = (
            (df["Fill Level (%)"] / 100) * 2 +
            (df["Tilt"] * 3) +
            (df["Temperature (°C)"] / 50) +
            (df["Humidity (%)"] / 100)
    )
    df.sort_values(by="Priority", ascending=False, inplace=True)
    return df


# Fetch and process live bin data
bin_data = generate_bin_data()
bin_data = calculate_priority(bin_data)


# Generate real-time van locations
def generate_van_data():
    return pd.DataFrame({
        "Van ID": [f"Van-{i + 1}" for i in range(4)],
        "Latitude": [random.uniform(28.5, 28.9) for _ in range(4)],
        "Longitude": [random.uniform(77.0, 77.5) for _ in range(4)]
    })


vans = generate_van_data()


# Assign bins dynamically to closest available vans
# Assign bins dynamically to closest available vans & send Twilio alerts
def assign_bins_to_vans(bin_data, vans):
    assignments = []

    for _, bin in bin_data.iterrows():
        min_distance = float('inf')
        assigned_van = None
        assigned_driver_number = None  # Store driver number for Twilio

        for _, van in vans.iterrows():
            distance = np.sqrt((bin["Latitude"] - van["Latitude"]) ** 2 + (bin["Longitude"] - van["Longitude"]) ** 2)
            if distance < min_distance:
                min_distance = distance
                assigned_van = van["Van ID"]
                assigned_driver_number = "+919810126223" # Replace with actual driver's number

        assignments.append(assigned_van)

        # 🚨 **Send SMS Notification via Twilio**


    bin_data["Assigned Van"] = assignments
    return bin_data


bin_data = assign_bins_to_vans(bin_data, vans)

# Display bin data in a table
st.subheader("\U0001F4CD Live Bin Status")
st.dataframe(
    bin_data.style.format({"Fill Level (%)": "{:.2f}", "Temperature (°C)": "{:.2f}", "Humidity (%)": "{:.2f}"}))

# Display bin locations on a map
st.subheader("\U0001F5FA️ Bin Locations & Routes")
map = folium.Map(location=[28.7, 77.2], zoom_start=12)
# Add dustbin markers
for _, bin in bin_data.iterrows():
    folium.Marker(
        location=[bin["Latitude"], bin["Longitude"]],
        popup=f"Bin ID: {bin['Bin ID']}<br>Fill Level: {bin['Fill Level (%)']}%",
        icon=folium.Icon(icon="trash", prefix="fa", color="black")
    ).add_to(map)





# Function to display selected van's route
# Dropdown to select a van
selected_van = st.selectbox("Select a Van to View Route", ["All"] + list(vans["Van ID"]))

# Function to display selected van's route and dustbin markers
def get_selected_van_route(selected_van, bin_data, vans, map_obj):
    colors = ["blue", "red", "green", "purple", "orange", "darkblue", "darkred", "darkgreen"]

    # Add dustbin markers first
    for _, bin in bin_data.iterrows():
        folium.Marker(
            location=[bin["Latitude"], bin["Longitude"]],
            popup=f"Bin ID: {bin['Bin ID']}<br>Fill Level: {bin['Fill Level (%)']}%",
            icon=folium.Icon(icon="trash", prefix="fa", color="black")
        ).add_to(map_obj)

    if selected_van == "All":
        # Show routes for all vans
        for i, van in vans.iterrows():
            assigned_bins = bin_data[bin_data["Assigned Van"] == van["Van ID"]]
            coordinates = [(row["Latitude"], row["Longitude"]) for _, row in assigned_bins.iterrows()]

            if coordinates:
                coordinates.insert(0, (van["Latitude"], van["Longitude"]))
                try:
                    directions = gmaps.directions(
                        origin=coordinates[0],
                        destination=coordinates[-1],
                        waypoints=coordinates[1:-1],
                        mode="driving"
                    )

                    route_coords = [(step['start_location']['lat'], step['start_location']['lng']) for leg in
                                    directions[0]['legs'] for step in leg['steps']]

                    path_color = colors[i % len(colors)]
                    folium.PolyLine(route_coords, color=path_color, weight=5, opacity=0.8).add_to(map_obj)

                    # Van Marker
                    folium.Marker(
                        [van["Latitude"], van["Longitude"]],
                        popup=f"Van: {van['Van ID']}",
                        icon=folium.Icon(color=path_color, icon="truck", prefix="fa")
                    ).add_to(map_obj)

                except Exception as e:
                    st.error(f"Error generating route for {van['Van ID']}: {e}")

    else:
        # Show route for selected van only
        van = vans[vans["Van ID"] == selected_van].iloc[0]
        assigned_bins = bin_data[bin_data["Assigned Van"] == selected_van]
        coordinates = [(row["Latitude"], row["Longitude"]) for _, row in assigned_bins.iterrows()]

        if coordinates:
            coordinates.insert(0, (van["Latitude"], van["Longitude"]))
            try:
                directions = gmaps.directions(
                    origin=coordinates[0],
                    destination=coordinates[-1],
                    waypoints=coordinates[1:-1],
                    mode="driving"
                )

                route_coords = [(step['start_location']['lat'], step['start_location']['lng']) for leg in
                                directions[0]['legs'] for step in leg['steps']]

                path_color = "blue"  # Fixed color for selected van
                folium.PolyLine(route_coords, color=path_color, weight=5, opacity=0.8).add_to(map_obj)

                # Van Marker
                folium.Marker(
                    [van["Latitude"], van["Longitude"]],
                    popup=f"Van: {van['Van ID']}",
                    icon=folium.Icon(color=path_color, icon="truck", prefix="fa")
                ).add_to(map_obj)

            except Exception as e:
                st.error(f"Error generating route for {selected_van}: {e}")

    return map_obj


# Generate the map based on selected van
map = folium.Map(location=[28.7, 77.2], zoom_start=12)
map = get_selected_van_route(selected_van, bin_data, vans, map)
folium_static(map)


# Function to send real-time updates via Twilio
def send_update_message(worker_phone, message):
    client.messages.create(
        body=message,
        from_=TWILIO_PHONE_NUMBER,
        to=worker_phone
    )


# Admin Panel for Managing Field Workers
if user_role == "Admin":
    st.sidebar.subheader("\U0001F477 Field Workers Management")
    workers = pd.DataFrame({
        "Worker ID": [101, 102, 103, 104],
        "Name": ["Rajesh", "Amit", "Pooja", "Suresh"],
        "Assigned Zone": ["North", "South", "East", "West"],
        "Phone": ["+918368164831", "+918368164831", "+917654321098", "+916543210987"]
    })
    st.sidebar.dataframe(workers)

    selected_worker = st.sidebar.selectbox("Assign Bin", bin_data["Bin ID"])
    selected_worker_id = st.sidebar.selectbox("Select Worker", workers["Worker ID"])
    worker_phone = workers.loc[workers["Worker ID"] == selected_worker_id, "Phone"].values[0]

    if st.sidebar.button("Assign Task"):
        task_message = f"Bin {selected_worker} has been assigned to you. Please collect the waste promptly."
        send_update_message(worker_phone, task_message)
        st.sidebar.success(f"Bin {selected_worker} assigned to Worker {selected_worker_id} with real-time update!")
def generate_monthly_waste_data():
    dates = pd.date_range(start="2024-01-01", periods=30, freq='D')
    data = []
    for bin_id in range(1, 11):
        for date in dates:
            waste_amount = random.uniform(20, 100)  # kg per day
            carbon_footprint = waste_amount * 2.52 / 1000  # kg CO2 per kg waste
            data.append({
                "Bin ID": f"Bin-{bin_id}",
                "Date": date,
                "Waste (kg)": waste_amount,
                "Carbon Footprint (kg CO2)": carbon_footprint
            })
    return pd.DataFrame(data)

# Fetch Data
monthly_waste_data = generate_monthly_waste_data()

# Display Data
st.subheader("📊 Monthly Waste Analysis")
st.dataframe(monthly_waste_data)

# Waste Trends Per Bin
fig = px.line(monthly_waste_data, x="Date", y="Waste (kg)", color="Bin ID",
              title="Waste Generation Trends per Dustbin")
st.plotly_chart(fig)

# Carbon Footprint Analysis
carbon_footprint_summary = monthly_waste_data.groupby("Date")["Carbon Footprint (kg CO2)"].sum().reset_index()
fig_carbon = px.line(carbon_footprint_summary, x="Date", y="Carbon Footprint (kg CO2)",
                      title="Daily Carbon Footprint Trend")
st.plotly_chart(fig_carbon)

# Summary Statistics
st.subheader("📌 Key Insights")
total_waste = monthly_waste_data["Waste (kg)"].sum()
total_carbon = monthly_waste_data["Carbon Footprint (kg CO2)"].sum()
max_waste_day = monthly_waste_data.groupby("Date")["Waste (kg)"].sum().idxmax()

st.write(f"- **Total Waste Generated in a Month:** {total_waste:.2f} kg")
st.write(f"- **Total Carbon Footprint for the Month:** {total_carbon:.2f} kg CO2")
st.write(f"- **Day with Highest Waste Generation:** {max_waste_day.date()}")

st.success("✅ Analytics Report Generated Successfully!")


st.success("✅ Dashboard Updated Successfully!")








