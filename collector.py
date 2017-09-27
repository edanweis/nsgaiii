# -*- coding: utf-8 -*-
from __future__ import division
import time, array, random, copy, math, sys, pprint
from itertools import chain
import itertools
from operator import attrgetter, itemgetter
import csv
import pandas as pd
import requests, arrow
import pydash, json
from pydash import pick_by
import googlemaps
from datetime import datetime
from dateutil import tz
from collections import Counter
import traceback, sys
import pyrebase
import os.path
import pprint as pp
import time
# These functions are helpers to calculate variables used in the objective functions

import ctypes
class SYSTEMTIME(ctypes.Structure):
    _fields_ = [
        ('wYear', ctypes.c_int16),
        ('wMonth', ctypes.c_int16),
        ('wDayOfWeek', ctypes.c_int16),
        ('wDay', ctypes.c_int16),
        ('wHour', ctypes.c_int16),
        ('wMinute', ctypes.c_int16),
        ('wSecond', ctypes.c_int16),
        ('wMilliseconds', ctypes.c_int16)]


def timenow():
	SystemTime = SYSTEMTIME()
	lpSystemTime = ctypes.pointer(SystemTime)
	ctypes.windll.kernel32.GetLocalTime(lpSystemTime)
	return arrow.get(" ".join([str(SystemTime.wYear), str(SystemTime.wMonth), str(SystemTime.wDay), str(SystemTime.wHour), str(SystemTime.wMinute), str(SystemTime.wSecond)])+" +10:00", 'YYYY M D H m s Z')

print("Time set to: %s" % timenow().humanize())


gmaps = googlemaps.Client(key='AIzaSyB3ZUNaFiXOQu3lZBtofgyFm7z8lhDGafc')
pd.set_option('display.max_info_columns', 20)
pd.set_option('display.max_columns', 20)

# data = pd.read_csv('nsga.csv', index_col=False, header=None)

def my_safe_repr(object, context, maxlevels, level):
    typ = pprint._type(object)
    if typ is unicode:
        object = str(object.encode('utf-8'))
    return pprint._safe_repr(object, context, maxlevels, level)

pp = pprint.PrettyPrinter(indent=4)
pp.format = my_safe_repr


def time_taken(seconds):
	m, s = divmod(seconds, 60)
	h, m = divmod(m, 60)
	return (h, m, s)

config = {
  "apiKey" : "AIzaSyCTnDTu6secmIbovYhWC75UBU3SfotQvMQ",
  "authDomain": "lch15018.firebaseapp.com",
  "databaseURL": "https://lch15018.firebaseio.com",
  "storageBucket": "lch15018.appspot.com",
}

firebase = pyrebase.initialize_app(config)




def travel_time(item, origin="Civic Square launceston"):
	if item.get('geometry', None):
		try:
			driving_directions = gmaps.directions(origin, [item['geometry']['coordinates']['latlng']['lat'], item['geometry']['coordinates']['latlng']['lng']], mode="driving", departure_time=timenow().shift(minutes=+15))
			bicycle_directions = gmaps.directions(origin, [item['geometry']['coordinates']['latlng']['lat'], item['geometry']['coordinates']['latlng']['lng']], mode="bicycling", departure_time=timenow().shift(minutes=+15))

			if bicycle_directions:
				bicycle_duration = int(bicycle_directions[0].get('legs', [])[0].get('duration', {}).get('value', None)) # minutes
				bicycle_distance = int(bicycle_directions[0].get('legs', [])[0].get('distance', {}).get('value', None)) # meters
			

			if driving_directions:
				mode = "driving"
				duration = int(driving_directions[0].get('legs', [])[0].get('duration_in_traffic', {}).get('value', None)) # minutes
				distance = int(driving_directions[0].get('legs', [])[0].get('distance', {}).get('value', None)) # meters
				if duration < 600:
					mode = "walking"
					walking_directions = gmaps.directions(origin, [item['geometry']['coordinates']['latlng']['lat'], item['geometry']['coordinates']['latlng']['lng']], mode="walking", departure_time=timenow().shift(minutes=+10))
					duration = int(walking_directions[0].get('legs', [])[0].get('duration', {}).get('value', None)) # minutes
					distance = int(walking_directions[0].get('legs', [])[0].get('distance', {}).get('value', None)) # meters
				
				return { 'duration': duration, 'distance': distance, 'mode': mode, 'bicycle_duration': bicycle_duration, 'bicycle_distance' : bicycle_distance }
			else: 
				return {}
		except Exception:
			print('error getting directions')
			print(traceback.format_exc())
			return {}
	else: 
		return {}

# parses opening time, closing time, minimum visit duration and open_now
# Todo: calculate next_open_time to notify when it's next open, by looking at the next item in list or using prev_day.
# open_now should be confirmed with API call in front-end.
# business hours may change, so keep updating the back-end JSON.
# open_time may not be needed, if it's always in the past?
# Watch out for other time text strings, other than "Open 24 hours", or "closed"
# 24 hour visits have maximum 24 hours -  not infinite hours.

def times(item):
	today = arrow.now().isoweekday()
	today_text = str(arrow.now().format('dddd'))
	close_time = "default"
	maximum_visit_duration = 0
	open_now = None
	try: 
		if item['activity'].get('opening_hours'):
			for text in item['activity']['opening_hours']['periods']['weekday_text']:
				t = text.encode('utf-8')
				if today_text in t:
					if "Open 24 hours" in t:
						# print "open 24 hours ------------------------------------------------------------------------------------------------------------------------"
						open_now = 1
						maximum_visit_duration = 24*3600
						ot = timenow().shift(days=+1)
						ct = timenow().shift(days=-1)
						return {"open_time" : ot.timestamp, "close_time":ct.timestamp, "open_now": open_now, "maximum_visit_duration": maximum_visit_duration }
					if "Closed" in t:
						open_now = 0
						maximum_visit_duration = 0
						ot = None
						ct = None
						return {"open_time" : ot, "close_time":ct, "open_now": open_now, "maximum_visit_duration": maximum_visit_duration }
		else:
			return {"open_time" : None, "close_time":None, "open_now": 0, "maximum_visit_duration": 0 }

		for index, period in enumerate(item['activity']['opening_hours']['periods']['periods']):			
			o_day = int(period['open']['day'])
			c_day = period.get('close', {}).get('day', None)
			ot = arrow.get(arrow.now().format(fmt='YYYY-MM-DD')+" "+period['open']['time'] + " +10:00", "YYYY-MM-DD HHmm Z")
			if c_day > o_day:  # if close time is greater than midnight, shift day by 24 hours.
				ct = arrow.get(arrow.now().shift(days=1).format(fmt='YYYY-MM-DD')+" "+period['close']['time'] + " +10:00", "YYYY-MM-DD HHmm Z")
			else:
				ct = arrow.get(arrow.now().format(fmt='YYYY-MM-DD')+" "+period['close']['time'] + " +10:00", "YYYY-MM-DD HHmm Z")

			if ot < arrow.now() < ct:
				open_now = 1
				maximum_visit_duration = round((ct - arrow.now()).total_seconds()/3600.00, 2)
				return {"open_time" : ot.timestamp, "close_time":ct.timestamp, "open_now": open_now, "maximum_visit_duration": maximum_visit_duration }

		return {"open_time" : ot.timestamp, "close_time":ct.timestamp, "open_now": open_now, "maximum_visit_duration": maximum_visit_duration }

	except KeyError:
		return {}
	except Exception:
		print(traceback.format_exc())
		return {}

def nearest(items, pivot):
    return min(items, key=lambda x: abs(x - pivot))

def get_weather():
	# from Willy weather API on launceston: 
	# {"units":{"distance":"km"},"location":{"id":10686,"name":"Launceston","region":"Northern","state":"TAS","postcode":"7250","timeZone":"Australia\/Hobart","lat":-41.44028,"lng":147.13935,"typeId":4,"distance":0.6}}
	weather_cont = {
		"fine" : 1,
		"mostly-fine" : 0.95,
		"high-cloud" : 0.85,
		"partly-cloudy" : 0.9,
		"mostly-cloudy" : 0.85,
		"cloudy" : 0.8,
		"overcast" : 0.7,
		"shower-or-two" : 0.6,
		"chance-shower-fine" : 0.75,
		"chance-shower-cloud" : 0.75,
		"drizzle" : 0.4,
		"few-showers" : 0.3,
		"showers-rain" : 0.2,
		"heavy-showers-rain" : 0.1,
		"chance-thunderstorm-fine" : 0.3,
		"chance-thunderstorm-cloud" : 0.2,
		"chance-thunderstorm-showers" : 0.1,
		"thunderstorm" : 0.1,
		"chance-snow-fine" : 0.3,
		"chance-snow-cloud" : 0.3,
		"snow-and-rain" : 0.1,
		"light-snow" : 0.1,
		"snow" : 0.2,
		"heavy-snow" : 0.1,
		"wind" : 0.7,
		"frost" : 0.4,
		"fog" : 0.6,
		"hail" : 0.1,
		"dust" : 0.5
	}

	r = requests.get('https://api.willyweather.com.au/v2/NWUxNzUxZWRhMGZiYmE5NWJiNGYyOD/locations/10686/weather.json?forecasts=weather,sunrisesunset,temperature,rainfallprobability&days=1')
	forecast = r.json()['forecasts']['rainfallprobability']['days'][0]['entries']
	forecast_formatted = [ arrow.get(x['dateTime']+'+10:00') for x in forecast]
	nearest_forecast = nearest(forecast_formatted, timenow())
	i = forecast_formatted.index(nearest_forecast)
	hrs = [ arrow.get(x['dateTime']+'+10:00').datetime.hour + arrow.get(x['dateTime']+'+10:00').datetime.minute / 60 for x in forecast]
	temps = [y['probability'] for y in forecast]
	rainfall_probability = forecast[i]['probability']
	# pp.pprint(r.json())

	weather_score = weather_cont[r.json()['forecasts']['weather']['days'][0]['entries'][0]['precisCode']]
	# from scipy.stats import linregress
	# print([y['probability'] for y in forecast])
	# reg = linregress(hrs, temps)
	# pp.pprint(reg)
	return {"rainfall_probability" : rainfall_probability,
			"sunset": arrow.get(r.json()['forecasts']['sunrisesunset']['days'][0]['entries'][0]['lastLightDateTime'] + "+10:00").timestamp,
			"weather": weather_score}


def suitable(item, group):
	return 1 if group in item['activity'].get('suitable', []) else 0

def avg_rating(item):
	l = item.get('social', {}).get('ratings', {}).values()
	return sum(l) / float(len(l)) if l else None

def number_reviews(item):
	# print(item['activity'].get('social', {})`.get('reviews', {}))
	reviews = item.get('social', {}).get('reviews', {})
	t = 0
	for key, value in reviews.iteritems():
		t +=len(value)
	return t

def eat_see_do(item):
	t = item['activity'].get('activityTypes', None)
	if t:
		try:
			return {
			'eat': t.count('eat')/float(len(t)),
			'see': t.count('see')/float(len(t)),
			'do': t.count('do')/float(len(t)) 
			}
		except Exception:
			print('error: eat_see_do')
			print(traceback.format_exc())
	else:
		return {}

def popularity(item, key):
	data = item['activity'].get('popular', None)
	# pp.pprint(data)
	if data:
		try:
			data = data[1:]
			df = pd.DataFrame(data)
			shift = 24-(24-(len(data)-1))
		
			# l = [ timenow().replace(hour=x+6, minute=0, second=0, microsecond=0).timestamp for x in list(df)]
		
			l = [ timenow().replace(hours=int(x), minute=0, second=0, microsecond=0).shift(hours=+int(shift)).timestamp for x in list(df)]
			# print([shift,key])
			h = nearest(list(df), int(timenow().shift(hours=-6).format('H')))
			time = timenow()
			day = time.shift(hours=+24).weekday()
			m_hour = df[h].mean()
			m_today = float(df.iloc[[day]].mean(axis=1))
			val = df.get_value(day,h)/100.00
			return { 'now': val, 'avg_current_hour': m_hour, 'avg_current_day': m_today }
			# else:
			# 	print('Popular times histogram longer than 17')
				# return {}
		except Exception:
			print('error: popularity')
			print(traceback.format_exc())
			return { }
	else:
		return { }

def mode_to_int(mode):
	if mode:
		d = {'walking': 0, 'driving' : 1}
		return d[mode]
	else:
		return None

def better_when_to_int(when):
	if when: 
		d = {'busy': 1, 'quiet' : 0, 'anytime': 2}
		return d[when]
	else:
		return None

def operatedBy(item):
	if item['activity'].get('operatedBy', None) == "business":
		return 0
	elif item['activity'].get('operatedBy', None) == "council":
		return 1
	elif item['activity'].get('operatedBy', None) == "public institution":
		return 2
	elif item['activity'].get('operatedBy', None) == "community":
		return 3

##############################################################################
##############################################################################

# This function prepares a dataframe with variables for use in
# calculating objective functions called from the NSGAiii algorithm.
# Synchronous http requests are performed now rather than at NSGAiii to save calc time.
# Variables are at their most granular for versatile re-use and explicit composition of objective function.


def collect_variables(start=0, end=571, save=True, floats_only=False, caching=True):
	st = time.time()
	if caching == False:
		print('fetching data from firebase... this may take a few minutes')
		db = firebase.database()
		items = db.child("scrape/edited/results").order_by_key().start_at(str(start)).end_at(str(end)).get()
		events = db.child("scrape/events").get()
		d = []
		# Get time-dependent, but lagging variables once-off to minimuse http requests.
		weather = get_weather()
		# build temporary JSON object for convenient conversion into pandas DataFrame
		
		for item in items.each():
			tt = travel_time(item.val()) 
			try:
				print(str(item.key().encode('utf-8'))+" "+item.val().get('name', '').encode('utf-8'))
				# print(str(item.key().encode('utf-8')) + " "+ times(item.val()))
				d.append({
					# "000_name": item.val().get('name', None),
					"001_.key": item.key(),
					"002_place": 1,
					"003_event": 0,
					"004_active": 0 if item.val()['activity'].get('active') == False else 1,
					"005_open_now": times(item.val()).get('open_now', None),
					"006_open_time": times(item.val()).get('open_time', None),
					"007_close_time": times(item.val()).get('close_time', None),
					"008_maximum_visit_duration": times(item.val()).get('maximum_visit_duration', None),
					"009_minimum_visit_duration": item.val()['activity'].get('visitTime', None),
					"010_travel_time": tt.get('duration', None),
					"011_travel_distance": tt.get('distance', None),
					"012_travel_mode": mode_to_int(tt.get('mode', None)),
					"013_rainfall": weather.get('rainfall_probability', None),
					"014_sunset": weather.get('sunset', None),
					"015_weather_score": weather.get('weather', None),
					"016_weather_dependent": round(item.val()['activity'].get('weatherDependent', 0.0001)/100.00, 2),
					"017_suitable_for_weather_score": round(item.val()['activity'].get('weatherCondition', 0.0001)/100.00, 2),
					"018_average_social_rating": avg_rating(item.val()),
					"019_number_reviews": number_reviews(item.val()),
					"020_suitable_for_children": suitable(item.val(), 'children'),
					"021_suitable_for_groups": suitable(item.val(), 'groups'),
					"022_suitable_for_vision_impaired": suitable(item.val(), 'vision impaired'),
					"023_suitable_for_bicycles": suitable(item.val(), 'bicycles'),
					"024_suitable_for_wheelchair": suitable(item.val(), 'wheelchair'),
					"025_eat": eat_see_do(item.val()).get('eat', None),
					"026_see": eat_see_do(item.val()).get('see', None),
					"027_do": eat_see_do(item.val()).get('do', None),
					"028_popularity_now": popularity(item.val(), item.key()).get('now', None),
					"029_popularity_avg_current_day": popularity(item.val(), item.key()).get('avg_current_day', None),
					"030_popularity_avg_current_hour": popularity(item.val(), item.key()).get('avg_current_hour', None),
					"031_better_when": better_when_to_int(item.val()['activity'].get('betterWhen', None)),
					"032_elevation": item.val()['activity'].get('elevation', None),
					"033_bicycle_duration": tt.get('bicycle_duration', None),
					"034_bicycle_distance": tt.get('bicycle_distance', None),
					"035_operated_by": operatedBy(item.val()),
				})
			except KeyboardInterrupt:
				break

		# for event in events.each():
		# 	try:
		# 		print(str(event.key()) +" "+event.val().get('name', ''))
		# 		d.append({
		# 			"place": 0,
		# 			"event": 1,
		# 			"active": event.val()['activity'].get('active'),
		# 			"name": event.val().get('name', ''),
		# 			"open_now": is_open(event.val()),
		# 			"open_time": open_time(event.val()),
		# 			"close_time": close_time(event.val()),
		# 			"maximum_visit_duration": maximum_visit_duration(event.val()),
		# 			"minimum_visit_duration": event.val()['activity'].get('visitTime', None),
		# 			"travel_time": travel_time(event.val()).get('duration', None),
		# 			"travel_distance": travel_time(event.val()).get('distance', None),
		# 			"rainfall": weather.get('rainfall_probability', None),
		# 			"sunset": weather.get('sunset', None),
		# 			"weather_score": weather.get('weather', None),
		# 			"weather_dependent": round(event.val()['activity'].get('weatherDependent', 0.0001)/100.00, 2),
		# 			"suitable_for_weather_score": round(event.val()['activity'].get('weatherCondition', 0.0001)/100.00, 2),
		# 			"average_social_rating": avg_rating(event.val()),
		# 			"number_reviews": number_reviews(event.val()),
		# 			"suitable_for_children": suitable(event.val(), 'children'),
		# 			"suitable_for_groups": suitable(event.val(), 'groups'),
		# 			"suitable_for_vision_impaired": suitable(event.val(), 'vision impaired'),
		# 			"suitable_for_bicycles": suitable(event.val(), 'bicycles'),
		# 			"suitable_for_wheelchair": suitable(event.val(), 'wheelchair'),
		# 			"eat": eat_see_do(event.val()).get('eat', None),
		# 			"see": eat_see_do(event.val()).get('see', None),
		# 			"do": eat_see_do(event.val()).get('do', None),
		# 			"popularity_now": popularity(event.val(), event.key()).get('now', None),
		# 			"popularity_avg_current_day": popularity(event.val(), event.key()).get('avg_current_day', None),
		# 			"popularity_avg_current_hour": popularity(event.val(), event.key()).get('avg_current_hour', None),
		# 			"better_when": event.val()['activity'].get('betterWhen', None),
		# 			"elevation": event.val()['activity'].get('elevation', None)
		# 		})
		# 	except KeyboardInterrupt:
		# 		break

		df = pd.DataFrame.from_records(d)
		df = df[df['004_active'] != 0]	
		df.sort_values(by='001_.key', inplace=True)
		if floats_only:
			df = df.select_dtypes(['number'])
		df['018_average_social_rating'].fillna((df['018_average_social_rating'].mean()), inplace=True)
		if save:
			df.to_csv('nsga.csv', encoding='utf-8', index=0)
		result =  df.itertuples()

	else:
		if os.path.isfile("nsga.csv"):
			print('reading cached data from file...')
			csv = pd.read_csv('nsga.csv')		
			result = csv.itertuples()

		else:
			print('No data.csv file found for caching. Try set caching=False, to prevent this.')
			print(traceback.format_exc())
			result = None	
	
	et = time.time()
	print "Finished in " + time.strftime('%H:%M:%S', time.gmtime(et-st))
	return result 