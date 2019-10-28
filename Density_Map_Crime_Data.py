import numpy as np
import sys
import cv2
import geocoder
import geopy.distance as gpy
from scipy import signal
import matplotlib.pyplot as plt
import math
year_month = '2019-07'
kernel = np.ones((100,100))/10000
g = geocoder.ipinfo('me')
input_latitude = g.latlng[0]
input_longitude = g.latlng[1]
input_coordinates = [input_latitude,input_longitude]
np.set_printoptions(threshold=sys.maxsize)
print(g.latlng)
f = 0.0714
print(gpy.distance(input_coordinates, (input_latitude, input_longitude + f)).miles)

def crime_location_filter(input_latitude, input_longitude,year_month):
    import requests
    import json
    url = "https://data.police.uk/api/crimes-street/all-crime?lat={}&lng={}&date={}&poly={},{}:{},{}:{},{}:{},{}".format(input_latitude, input_longitude, year_month, input_latitude - 0.0435, input_longitude - f, input_latitude + 0.0435, input_longitude - f, input_latitude - 0.0435, input_longitude + f, input_latitude + 0.0435, input_longitude + f)
    requests = requests.get(url)
    crime_data = requests.json()
    crime_type = []
    crime_latitude = []
    crime_longitude = []
    for i in range(len(crime_data)-1):
        crime_type2 = crime_data[i]['category']
        crime_type.append(crime_type2)
        crime_longitude.append(crime_data[i]['location']['longitude'])
        crime_latitude.append(crime_data[i]['location']['latitude'])
    # data = pd.read_csv("2019-08-cambridgeshire-street.csv",None)
    # crime_type = data['Crime type'].values
    crime_types = np.unique(crime_type)
    crime_weighting = [5 for i in range(len(crime_type)-1)]
    crime_dictionary = dict(zip(crime_types,crime_weighting))
    # crime_latitude = data['Latitude'].values
    # crime_longitude = data['Longitude'].values
    final_crime_coordinates = []
    for i in range(len(crime_latitude)-1):
        final_crime_coordinates.append((round(float(crime_longitude[i]),4),round(float(crime_latitude[i]),4)))
    coordinate_crimetype_dict = dict(zip(final_crime_coordinates,crime_type))

    return final_crime_coordinates, crime_type, crime_weighting, crime_latitude, crime_longitude,coordinate_crimetype_dict, crime_dictionary

def density_map_generator():
    cc, ct, cw,clat,clon,ccd, crime_dict = crime_location_filter(input_latitude,input_longitude,year_month)

    coordinate_meshgrid = np.zeros((int(math.floor((input_longitude + f) * 10000) - math.floor((input_longitude - f) * 10000)), int(math.floor((input_latitude + 0.0435) * 10000) - math.floor((input_latitude - 0.0435) * 10000))))
    latitude_matrix = np.zeros((int(math.floor((input_longitude + f) * 10000) - math.floor((input_longitude - f) * 10000)), int(math.floor((input_latitude + 0.0435) * 10000) - math.floor((input_latitude - 0.0435) * 10000))))
    longitude_matrix = np.zeros((int(math.floor((input_longitude + f) * 10000) - math.floor((input_longitude - f) * 10000)), int(math.floor((input_latitude + 0.0435) * 10000) - math.floor((input_latitude - 0.0435) * 10000))))

    for i in range(math.floor((input_longitude - f) * 10000), math.floor((input_longitude + f) * 10000)):
        for j in range(math.floor((input_latitude-0.0435)*10000), math.floor((input_latitude+0.0435)*10000)):
            # print(i-math.floor((input_longitude-0.0119)*10000),j-(input_latitude-0.0145)*10000)

            if (round(float(i/10000),4),round(float(j/10000),4)) in cc:
                # print(i-math.floor((input_longitude-0.0119)*10000),j-math.floor((input_latitude-0.0145)*10000))
                coordinate_meshgrid[i - math.floor((input_longitude - f) * 10000), j - math.floor((input_latitude - 0.0435) * 10000)] = float(crime_dict[ccd[round(float(i / 10000), 4), round(float(j / 10000), 4)]])
                latitude_matrix[i - math.floor((input_longitude - f) * 10000), j - math.floor((input_latitude - 0.0435) * 10000)] = j / 10000
                longitude_matrix[i - math.floor((input_longitude - f) * 10000), j - math.floor((input_latitude - 0.0435) * 10000)] = i / 10000
            else:
                try:
                    coordinate_meshgrid[i - math.floor((input_longitude - f) * 10000), j - math.floor((input_latitude - 0.0435) * 10000)] = 0
                except IndexError:
                    break;

    grad = signal.convolve2d(coordinate_meshgrid, kernel, 'same')
    unrolled_density = grad.ravel()
    unrolled_latitude = list(latitude_matrix.ravel())
    unrolled_longitude = list(longitude_matrix.ravel())
    x = []
    y = []
    z = []

    for i in range(len(unrolled_latitude)-1):
        if unrolled_latitude[i] != 0 and unrolled_longitude[i] != 0:
                y.append(unrolled_latitude[i])
                x.append(unrolled_longitude[i])
                z.append(unrolled_density[i])
    unrolled_latitude = y
    unrolled_longitude = x
    unrolled_density = z
    a = [min(x), max(x),min(y), max(y)]

    plt.imshow(grad, extent=a)
    plt.show()
    return
