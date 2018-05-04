from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from bs4 import Tag
import re
import json
import time
import pickle
import urllib
import os.path
import getpass
import argparse
import operator
import http.cookiejar

DATA_FILE = 'trips.dat'

class Trip:
	def __str__(self):
		return self.date + ': from ' + str(self.p_from) + ' to ' + str(self.p_to) + ' (' + str(self.info_bike) + '), ' + str(self.info_distance) + 'km, ' + secondsToString(self.info_time) + ' '
	
cookies = http.cookiejar.CookieJar()

def loadStorage():
	global login, pin, trips
	login = ''
	trips = []
	if not os.path.isfile(DATA_FILE): return
	
	with open(DATA_FILE, 'rb') as f:
		data = pickle.load(f)
	login = data[0]
	pin = data[1]
	trips = data[2]

def saveStorage():
	data = (login, pin, trips)
	with open(DATA_FILE, 'wb') as f:
		pickle.dump(data, f)

def createCookedUrlOpener():
	return urllib.request.build_opener(
		urllib.request.HTTPRedirectHandler(),
		urllib.request.HTTPHandler(debuglevel=0),
		urllib.request.HTTPSHandler(debuglevel=0),
		urllib.request.HTTPCookieProcessor(cookies))
		
def requestAuth():
	global login, pin
	login = input("Enter login: ")
	pin = getpass.getpass("Enter pin: ")
	print()

def authenticateOnServer():
	url = 'https://velobike.ru/api/login/'
	values = {'login' : login, 'pin' : pin}
	data = urllib.parse.urlencode(values).encode("utf-8")
	req = urllib.request.Request(url, data)
	response = createCookedUrlOpener().open(req)
	return json.load(response)['status'] == "ok"
	
def parseArguments():
	parser = argparse.ArgumentParser()
	parser.add_argument("-sp", "--start_page", help="Scan from the specified page number", type=int, default=1)
	parser.add_argument("-ep", "--end_page", help="Scan to the specified page number", type=int, default=None)
	parser.add_argument("-md", "--minimum_distance", help="Minimum distance to count in fastest trips report", type=int, default=0)
	args = parser.parse_args()
	global sp, ep, md
	sp = args.start_page
	ep = args.end_page
	md = args.minimum_distance

def secondsToString(time_sec):
	return time.strftime('%H:%M:%S', time.gmtime(time_sec))

def grabTrips():
	opener = createCookedUrlOpener()
	local_trips = []
	page = sp
	presents = True
	storageReached = False
	while (presents and not storageReached and ((ep is None) or (page <= ep))):
		print('Parsing page', page)
		response = opener.open('https://velobike.ru/account/history/?page=' + str(page))
		html = response.read()
		
		parsed_html = BeautifulSoup(html, "html.parser")
		list = parsed_html.find('ul', class_="history-list")
		if not (list is None):
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
				time_val = str(holder.find('span', class_='routes-list__time').string.encode('utf-8'))
				distance = str(holder.find('span', class_='routes-list__distance').string.encode('utf-8'))
				trip = Trip()
				trip.date = item.find('span', class_='history-list__date').text
				trip.p_from = int(re.search('.*(\d{4})', point_from).group(1))
				trip.p_to = int(re.search('.*(\d{4})', point_to).group(1))
				trip.info_bike = str(holder.find('span', class_='routes-list__bike').string)
				trip.info_time = (datetime.strptime(re.search('b\'(.*)\'', time_val).group(1), '%H:%M:%S') - datetime(1900, 1, 1)).total_seconds()
				trip.info_distance = float(re.search('([\d\.]*) ', distance).group(1))
				if any(x for x in trips if x.date == trip.date and x.p_from == trip.p_from \
						and x.p_to == trip.p_to and x.info_bike == trip.info_bike and x.info_time == trip.info_time):
					storageReached = True
					break;
				local_trips.append(trip)
		presents = not (parsed_html.find('a', class_="btn-arrow-forward") is None or list is None)
		#presents = False
		page = page + 1
	trips[0:0] = local_trips
	print()
	
def appendToDictionary(dict, key, value = 1):
	if key in dict:
		dict[key] = dict[key] + value
	else:
		dict[key] = value
		
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
	# Max kms, max time
	# Max kms in day, max time in day, max trips per day (day value)
	# Used stations
	# Used bikes
	# 10 Fastest trips, used bikes
	# 10 Longest trips, used bikes
	days = {}
	days_kms = {}
	days_time = {}
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
		appendToDictionary(days_kms, trip.date, trip.info_distance)
		appendToDictionary(days_time, trip.date, trip.info_time)
		appendToDictionary(stations, trip.p_from)
		appendToDictionary(stations, trip.p_to)
		appendToDictionary(bikes, trip.info_bike)
		if trip.info_distance >= md:
			speed = trip.info_distance * 3600 / trip.info_time if trip.info_time else 0
			trips_speed[trip] = speed
	
	max_day = max(days.items(), key=operator.itemgetter(1))[0]
	max_day_kms	= max(days_kms.items(), key=operator.itemgetter(1))[0]
	max_day_time = max(days_time.items(), key=operator.itemgetter(1))[0]
	sorted_stations = sorted(stations.items(), key=operator.itemgetter(1, 0), reverse=True)
	sorted_bikes = sorted(bikes.items(), key=operator.itemgetter(1, 0), reverse=True)
	sorted_speed = sorted(trips_speed.items(), key=operator.itemgetter(1), reverse=True)
	sorted_len = sorted(trips, key=lambda x: -x.info_distance)
	sorted_time = sorted(trips, key=lambda x: -x.info_time)
	print('Total trips: {0}, total kms: {1}, total time: {2}'.format(len(trips), round(total_kms), timedelta(seconds=total_time)))
	if len(trips) > 0: print('Avg kms: {0}, avg time: {1}, avg speed: {2}'.format(round(total_kms / len(trips), 2), secondsToString(total_time / len(trips)), round(total_kms * 3600 / total_time, 1)))
	print('Max kms: {0}, max time: {1}'.format(max_kms, secondsToString(max_time)))
	print('Max kms in day: {0} ({1}), max time in day: {2} ({3}), max trips per day: {4} ({5})\n'.format(days_kms[max_day_kms], max_day_kms, secondsToString(days_time[max_day_time]), max_day_time, days[max_day], max_day))
	print('Used stations ({0}):\n{1}\n'.format(len(sorted_stations), tupleListToString(sorted_stations, False)))
	print('Used bikes ({0}):\n{1}\n'.format(len(sorted_bikes), tupleListToString(sorted_bikes, False)))
	print('Fastest trips:\n{0}\n'.format(tupleListToString(sorted_speed[0:10], True)))
	print('Longest trips:')
	printTrips(sorted_len[0:10])
	print()
	print('All trips:')
	printTrips(trips)
	return
	
parseArguments()
loadStorage()
if login == '':
	requestAuth()
if authenticateOnServer():	
	grabTrips()
	saveStorage()
	processTrips(trips)	
else:
	print('Wrong credentials!')