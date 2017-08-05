from bs4 import BeautifulSoup
from bs4 import Tag
import re
import json
import urllib
import getpass
import operator
import http.cookiejar

class Trip:
	def __str__(self):
		return self.date + ': from ' + str(self.p_from) + ' to ' + str(self.p_to) + ' (' + str(self.info_bike) + '), ' + str(self.info_distance) + 'km, ' + str(self.info_time) + ' min '
	
cookies = http.cookiejar.CookieJar()

def createCookedUrlOpener():
	return urllib.request.build_opener(
		urllib.request.HTTPRedirectHandler(),
		urllib.request.HTTPHandler(debuglevel=0),
		urllib.request.HTTPSHandler(debuglevel=0),
		urllib.request.HTTPCookieProcessor(cookies))

def authenticateOnServer():
	login = input("Enter login: ")
	pin = getpass.getpass("Enter pin: ")
	print()
	url = 'https://velobike.ru/api/login/'
	values = {'login' : login, 'pin' : pin}
	data = urllib.parse.urlencode(values).encode("utf-8")
	req = urllib.request.Request(url, data)
	response = createCookedUrlOpener().open(req)
	return json.load(response)['status'] == "ok"

def grabTrips():
	trips = []
	opener = createCookedUrlOpener()
	page = 1
	presents = True
	while (presents):
		print('Parsing page', page)
		response = opener.open('https://velobike.ru/account/history/?page=' + str(page))
		html = response.read()
		
		parsed_html = BeautifulSoup(html, "html.parser")
		list = parsed_html.find('ul', class_="history-list")
		for item in list.contents:
			if not isinstance(item, Tag):
				continue
			if not item['class'][0] == 'history-list__item':
				continue
			if not (item.find('div', class_='card-preview') is None):
				continue
			holder = item.find('div', class_='history-list__holder')
			point_from = str(holder.find_all('span', class_='route-info__point-title')[0].text.encode('utf-8'))
			point_to = str(holder.find_all('span', class_='route-info__point-title')[1].text.encode('utf-8'))
			time = str(holder.find('span', class_='routes-list__time').string.encode('utf-8'))
			distance = str(holder.find('span', class_='routes-list__distance').string.encode('utf-8'))
			trip = Trip()
			trip.date = item.find('span', class_='history-list__date').text
			trip.p_from = int(re.search('.*(\d{4})', point_from).group(1))
			trip.p_to = int(re.search('.*(\d{4})', point_to).group(1))
			trip.info_bike = holder.find('span', class_='routes-list__bike').string
			trip.info_time = int(re.search('~ (\d*) ', time).group(1))
			trip.info_distance = float(re.search('([\d\.]*) ', distance).group(1))
			trips.append(trip)
		presents = not (parsed_html.find('a', class_="btn-arrow-forward") is None)
		#presents = False
		page = page + 1
	print()
	return trips
	
def appendToDictionary(dict, value):
	if value in dict:
		dict[value] = dict[value] + 1
	else:
		dict[value] = 1
		
def tupleListToString(list, separateLines):
	str_result = ""
	for tuple in list:
		if len(str_result) > 0:
			str_result += '\n' if separateLines else ', '
		str_result += str(tuple[0]) + '(' + str(round(tuple[1], 1)) + ')'
	return str_result
	
def printTrips(trips):
	for trip in trips:
		print(str(trip))
	return

def processTrips(trips):
	# Total trips, total kms, total time
	# Avg kms, avg time, avg speed
	# Max kms, max time, max per day (day)
	# Used stations
	# Used bikes
	# 10 Fastest trips, used bikes
	# 10 Longest trips, used bikes
	days = {}
	bikes = {}
	stations = {}
	trips_speed = {}
	max_kms = 0
	max_time = 0
	total_kms = 0
	total_time = 0
	for trip in trips:
		if trip.info_distance > max_kms:
			max_kms = trip.info_distance
		if trip.info_time > max_time:
			max_time = trip.info_time
		total_kms += trip.info_distance
		total_time += trip.info_time
		appendToDictionary(days, trip.date)
		appendToDictionary(stations, trip.p_from)
		appendToDictionary(stations, trip.p_to)
		appendToDictionary(bikes, trip.info_bike)
		speed = trip.info_distance * 60 / trip.info_time if trip.info_time else 0
		trips_speed[trip] = speed
	
	max_day = max(days.items(), key=operator.itemgetter(1))[0]
	sorted_stations = sorted(stations.items(), key=operator.itemgetter(1, 0), reverse=True)
	sorted_bikes = sorted(bikes.items(), key=operator.itemgetter(1, 0), reverse=True)
	sorted_speed = sorted(trips_speed.items(), key=operator.itemgetter(1), reverse=True)
	sorted_len = sorted(trips, key=lambda x: -x.info_distance)
	sorted_time = sorted(trips, key=lambda x: -x.info_time)
	print('Total trips:', len(trips), ', total kms:', round(total_kms), ', total time:', total_time)
	if len(trips) > 0: print('Avg kms:', round(total_kms / len(trips), 2), ', avg time:', round(total_time / len(trips), 2), ', avg speed:', round(total_kms * 60 / total_time, 1))
	print('Max kms:', max_kms, ', max time:', max_time, ', max trips per day:', days[max_day], '(', max_day, ')')
	print('Used stations:', tupleListToString(sorted_stations, False))
	print('Used bikes:', tupleListToString(sorted_bikes, False))
	print()
	print('Fastest trips:\n', tupleListToString(sorted_speed[0:10], True))
	print()
	print('Longest trips:')
	printTrips(sorted_len[0:10])
	print()
	print('All trips:')
	printTrips(trips)
	return
	
if authenticateOnServer():
	trips = grabTrips()
	processTrips(trips)
else:
	print('Wrong credentials!')