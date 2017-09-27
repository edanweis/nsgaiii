# -*- coding: utf-8 -*-
import googlemaps
import requests, arrow
import pyrebase
import traceback, sys
import re

config = {
  "apiKey" : "AIzaSyCTnDTu6secmIbovYhWC75UBU3SfotQvMQ",
  "authDomain": "lch15018.firebaseapp.com",
  "databaseURL": "https://lch15018.firebaseio.com",
  "storageBucket": "lch15018.appspot.com",
}

firebase = pyrebase.initialize_app(config)


# parses opening time, closing time, minimum visit duration and open_now
# open_now should be confirmed with API call in front-end.
# business hours may change, so keep updating the back-end JSON.
# open_time may not be needed, if it's always in the past?
# next_open_time might be a good idea, to notify when it's next open.
# Watch out for other time text strings, other than "Open 24 hours", or "closed"

def times(item):
	day = str(arrow.now().format('dddd'))
	try:
		close_time = None
		open_time = None
		open_now = 0
		maximum_visit_duration = 0
		for index, text in enumerate(item['activity']['opening_hours']['periods']['weekday_text']):			
			prev_day = []
			t = text.encode('utf-8')
			if day in t:
				prev_day = item['activity']['opening_hours']['periods']['weekday_text'][index-1]
				# print prev_day.encode('utf-8')
				h = t.replace(day+":", "")
				if "Open 24 hours" in h:
					return {"open_now": 1, "maximum_visit_duration": 24*3600, "close_time": arrow.now().shift(days=+1).timestamp, "open_time": arrow.now().shift(days=-1).timestamp }
				if "Closed" in h:
					return {"open_now": 0, "maximum_visit_duration": 0, "close_time": None, "open_time": None }
				h = h.split(",")
				h = [[z.strip() for z in z.split("–")] for z in h]
				for ix, l in enumerate(h):
					for idx, z in enumerate(l):
						if z[-1] != 'M':
							try:
								h[ix][idx] = z+ " " + l[idx+1][-2:]
							except IndexError:
								h[ix][idx] = z+ " " + l[idx-1][-2:]
				for m in h:	
					ranges = []
					for s in m:
						ranges.append([ arrow.get(arrow.now().format(fmt='YYYY-MM-DD')+" "+ s + " +1000", "YYYY-MM-DD h:mm A Z") for s in m])
					for ra in ranges:
						if ra[0] < arrow.now() < ra[1]:
							close_time = ra[1]
							open_time = ra[0]
							open_now = 1
							maximum_visit_duration = round((close_time - arrow.now()).total_seconds()/3600.00, 2)
				return {"open_time" : open_time, "close_time":close_time, "open_now": open_now, "maximum_visit_duration": maximum_visit_duration }
	except Exception:
		return None


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

def dayofmonth():
	SystemTime = SYSTEMTIME()
	lpSystemTime = ctypes.pointer(SystemTime)
	ctypes.windll.kernel32.GetLocalTime(lpSystemTime)
	return str(SystemTime.wDay)


def times2(item):
	today = arrow.now().isoweekday()
	today_text = str(arrow.now().format('dddd'))
	close_time = "default"
	open_time = None
	open_now = 0
	maximum_visit_duration = 0
	periods = []
	try: 
		try:
			if item['activity'].get('opening_hours'):
				for text in item['activity']['opening_hours']['periods']['weekday_text']:
					t = text.encode('utf-8')
					if today_text in t:
						if "Open 24 hours" in t:
							print "open 24 hours ------------------------------------------------------------------------------------------------------------------------"
							open_now = 1
							maximum_visit_duration = 24*3600
							ot = timenow().shift(days=+1)
							ct = timenow().shift(days=-1)
							return {"open_time" : ot.humanize(), "close_time":ct.humanize(), "open_now": open_now, "maximum_visit_duration": maximum_visit_duration }
						if "Closed" in t:
							open_now = 0
							maximum_visit_duration = 0
							ot = None
							ct = None
							return {"open_time" : ot, "close_time":ct, "open_now": open_now, "maximum_visit_duration": maximum_visit_duration }

		except Exception:
			print(traceback.format_exc())

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
				return {"open_time" : ot.humanize(), "close_time":ct.humanize(), "open_now": open_now, "maximum_visit_duration": maximum_visit_duration }

		return {"open_time" : ot.humanize(), "close_time":ct.humanize(), "open_now": open_now, "maximum_visit_duration": maximum_visit_duration }

	except KeyError:
		return {}
		pass
	except Exception:
		print(traceback.format_exc())
		return {}


def nearest(items, pivot):
    return min(items, key=lambda x: abs(x - pivot))

db = firebase.database()
items = db.child("scrape/edited/results").order_by_key().start_at(str(113)).end_at(str(113)).get()

for item in items.each():
	# print(timenow())
	# print(str(item.key())+" "+item.val().get('name', ''))
	print(str(item.key().encode('utf-8'))+" "+item.val().get('name', '').encode('utf-8'))
	try:
		print(times2(item.val()))
		# times(item.val())
		# print [x[0].encode('utf-8') for x in item.val()['activity']['opening_hours']['periods']['weekday_text'] ]
	except:
		pass
	# print(times2(item.val()))
	# print(open_time(item.val()))
	# try:
	# 	for i in item.val()['activity']['opening_hours']['periods']['weekday_text']:
	# 		print i.encode('utf-8')
	# except Exception:
	# 	print(traceback.format_exc())
		# pass

	
