import requests
import time
import csv
import re
import json
import pandas as pd
import random
import numpy as np


region_lookup = pd.read_csv('../data/region_to_area_name.csv')
us_regions = region_lookup[region_lookup['country'] == 'US']

# Initialize an empty list to store the data
data_list = []
max_listings = 10000 #number of search results to include, will return this number or less if there aren't that many
within_last_30 = 1 #1 means include listings from last 30 days, 0 means include from last 45 days

#415 in total
for index, row in us_regions.head(2).iterrows():  # Iterate through the first 2 rows in us_regions DataFrame
    time.sleep(random.randint(1, 3))  # Pause the loop for a random interval between 1 to 3 seconds to avoid overwhelming the server
    region_code = row['regionCode']
    region_name = row['region'] 
    code = row['code'] #region code for craigslist region, e.g. 656=Missoula
    #URL includes
    url = f"https://sapi.craigslist.org/web/v8/postings/search/full?CC=US&availabilityMode={within_last_30}&batch={code}-0-{max_listings}-0-0-1&lang=en&searchPath=apa"
    # Make the HTTP request
    response = requests.get(url)
    if response.status_code == 200:
        json_string = re.search(r'cl\.jsonp\(.*?,\s*(.*)\)', response.text).group(1) #extract everything inside parenthesis cl.jsonp()
        data = json.loads(json_string)
        listings = data['data']['items'] #each "item": is a dictionary of arrays, the first element of each array is a key
        for listing in listings:
            title = next((item[1] for item in listing if isinstance(item, list) and item[0] == 6), None) #6 is key for title section
            price = next((item[1] for item in listing if isinstance(item, list) and item[0] == 10), None) #10 is key for price section
            bedrooms = next((item[1] for item in listing if isinstance(item, list) and item[0] == 5), None) #5 is key for more info section, includes bedrooms and sqft
            
            # Extract square feet, assuming it follows the bedrooms value
            square_feet = next((item[2] for item in listing if isinstance(item, list) and item[0] == 5 and len(item) > 2), None)
            
            if isinstance(listing[4], str) and '~' in listing[4]: #sometimes lat/lon is missing but if its there this is its form
                _, latitude, longitude = listing[4].split('~')
            else:
                latitude, longitude = None, None
            
            # Append the extracted data to the list as a dictionary, including region and regionCode
            data_list.append({
                "title": title,
                "price": price,
                "bedrooms": bedrooms,
                "square_feet": square_feet,
                "latitude": latitude,
                "longitude": longitude,
                "region": region_name,  # Add region name to the dictionary
                "region_code": region_code  # Add region code to the dictionary
            })

# Convert the list of dictionaries to a DataFrame
df = pd.DataFrame(data_list)

# Convert 'price' from a string to a float
df['price'] = df['price'].replace('[\$,]', '', regex=True).astype(float)

# Now you can calculate 'price_per_bedroom' and 'price_per_sqft'
df['price_per_bedroom'] = df['price'] / df['bedrooms']
df['price_per_sqft'] = df['price'] / df['square_feet']

# Group the DataFrame by 'region' and calculate the median 'price_per_bedroom' and 'price_per_sqft' for each region
region_grouped_df = df.groupby('region').agg({
    'price_per_bedroom': 'median',
    'price_per_sqft': 'median'
}).reset_index()

# Rename columns for clarity
region_grouped_df.rename(columns={
    'price_per_bedroom': 'median_price_per_bedroom',
    'price_per_sqft': 'median_price_per_sqft'
}, inplace=True)
import datetime

# Add a column with the current datetime
region_grouped_df['datetime_now'] = datetime.datetime.now()

