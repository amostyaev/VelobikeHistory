# The script shows velobike stations on the Google map, station color marker depends on visit count
# Use `write_user_stations` to view all visited stations and `write_all_stations` to view all stations
#
# Setup & run
# 1) Run `velobike_history.py` script to load all trips statistics
# 2) Run `velobike_maps.py` script to generate JSON data object 
# 3) Open `velomap.html` to view the data

import sys
import json
from velobike_history import Trip
from velobike_history import loadTrips as load_trips

STATIONS_DATA_FILE = 'stations_data.json'
STATIONS_MAP_FILE = 'velomap.json'

def append_to_dictionary(dict, key, value = 1):
    if key in dict:
        dict[key] = dict[key] + value
    else:
        dict[key] = value
        
def get_stations_list(trips):
    stations = {}
    for trip in trips:
        append_to_dictionary(stations, trip.p_to)
        append_to_dictionary(stations, trip.p_from)
    return stations
    
def get_stations_locations():
    locations = {}
    with open(STATIONS_DATA_FILE) as json_file:
        data = json.load(json_file)    
    for station in data['Items']:
        locations[int(station['Id'])] = (station['Position']['Lat'], station['Position']['Lon'])
    return locations
    
def write_user_stations(stations, locations):
    data = []
    for item in stations.items():
        station = item[0]
        frequency = item[1]
        if station in locations:
            location = locations[station]
            data.append({'station': station, 'lat': location[0], 'lon': location[1], 'frequency': frequency, 'visited': True})
        else:
            print('Unable to locate the {st} station!'.format(st=station))
    with open(STATIONS_MAP_FILE, 'w') as text_file:
        print("locations = {}".format(json.dumps(data)), file=text_file)
    return
    
def write_all_stations(stations, locations):
    data = []
    for item in locations.items():
        station = item[0]
        location = item[1]
        visited = True if station in stations else False
        frequency = stations[station] if station in stations else 0
        data.append({'station': station, 'lat': location[0], 'lon': location[1], 'frequency': frequency, 'visited': visited})
        
    with open(STATIONS_MAP_FILE, 'w') as text_file:
        print("locations = {}".format(json.dumps(data)), file=text_file)
    return

def main(argv):
    trips = load_trips()
    stations = get_stations_list(trips)
    locations = get_stations_locations()
    write_user_stations(stations, locations)
    #write_all_stations(stations, locations)
    return
    
if __name__ == "__main__":
    main(sys.argv)