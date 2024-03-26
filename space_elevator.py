# -*- coding: utf-8 -*-
"""
Created on Fri Jul 14 16:02:53 2023

@author: jakef
"""

from geopy.geocoders import Nominatim
import time
import re
from os import walk


def extract_state_strings(lines):
    pattern = r"\bSTATE_(\w+)\b"
    state_strings = []

    for line in lines:
        matches = re.findall(pattern, line)
        state_strings.extend(matches)

    return state_strings


# Initialize geolocator
geolocator = Nominatim(user_agent="GettingLocationLatJake", timeout=10)


# Function to get the latitude
def get_latitude(place):
    location = geolocator.geocode(place)
    if location is not None:
        return location.latitude
    else:
        return None


# Read locations from file
locations = []
path = r"G:\SteamLibrary\steamapps\common\Victoria 3\game\map_data\state_regions"
filenames = next(walk(path), (None, None, []))[2]
for filename in filenames:
    with open(path + "/" + filename, "r") as f:
        lines = [line.strip() for line in f]
        states = extract_state_strings(lines)
        locations += states


# Filter locations
filtered_locations = []
for location in locations:
    latitude = get_latitude(location)
    # Check if within 10 degrees of the equator
    if latitude is not None and -10 <= latitude <= 10:
        filtered_locations.append(location)
        print("YES: ", location)
    elif location is None:
        print("NONE: ", location)
    else:
        print("NO: ", location)
    time.sleep(0.05)  # Respect the API rate limit

# Output locations
for location in filtered_locations:
    print(
        "                state_region = s:STATE_" + location.upper().replace(" ", "_")
    )
