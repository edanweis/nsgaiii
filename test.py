import requests, pprint, arrow
pp = pprint.PrettyPrinter(indent=4)

leave_in = 30
departure_time = arrow.utcnow().shift( minutes=+ leave_in ).timestamp


payload = {
	'origin': 'place_id:ChIJm6BDq9-mcKoRoGPcBH4BYFU',
	'destination': 'place_id:ChIJ-eUUatymcKoRgzStgmdAyrI',
	'mode': 'walking',
	'key': 'AIzaSyB3ZUNaFiXOQu3lZBtofgyFm7z8lhDGafc',
	'departure_time': departure_time
}

rp = requests.get("https://maps.googleapis.com/maps/api/directions/json", params=payload)
distance = rp.json()['routes'][0]['legs'][0]['distance']['value'] # meters
time = rp.json()['routes'][0]['legs'][0]['duration']['value'] # seconds

# print(arrow.utcnow().shift( minutes=+ leave_in ).timestamp)

if rp.json()['status'] == 'OK':
	print(time, distance)
else:
	print('error')