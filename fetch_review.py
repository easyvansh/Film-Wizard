import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import bs4 as bs
import urllib.request
from datetime import date, datetime
import requests
from requests_html import HTMLSession
from bs4 import BeautifulSoup 

def generate_id(name):
    session = HTMLSession()
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36",
        "Referer": "https://www.imdb.com/"
    }
    baseURL = "https://www.imdb.com"
    search_results = {'result_count': 0, 'results': []}
    assert isinstance(name, str)
    search_results = {}
    name = name.replace(" ", "+")
    url = f"https://www.imdb.com/find?q={name}&s=tt&exact=true&ref_=fn_tt_ex"
    try:
        response = session.get(url)
    except requests.exceptions.ConnectionError as e:
        response = session.get(url, verify=False)
    results = response.html.xpath(
        "//section[@data-testid='find-results-section-title']/div/ul/li")
    output = []
    result = results[0]
    # name = result.text.replace('\n', ' ')
    url = result.find('a')[0].attrs['href']
    file_id = url.split('/')[2]
    movie_url = ''.join(baseURL+'/title/'+file_id)
    try:
        response = requests.get(movie_url).content
    except requests.exceptions.ConnectionError as e:
        response = requests.get(movie_url, verify=False)
    soup = BeautifulSoup(response, 'html.parser')
    poster = ''
    # for item in soup.find('a')all.attrs['href']
    print()

    return file_id
    



def recommend(name):

    imdb_id = generate_id(name)
    
    movie_review_list= []

    if(imdb_id != ""):
        # web scraping to get user reviews from IMDB site
        # sauce = urllib.request.urlopen('https://www.imdb.com/title/{}/reviews?ref_=tt_ov_rt'.format(imdb_id)).read()
        sauce = urllib.request.urlopen('https://www.imdb.com/title/{}/reviews?ref_=tt_ov_rt'.format(imdb_id)).read()
        soup = bs.BeautifulSoup(sauce,'lxml')
        soup_result = soup.find_all("div",{"class":"text show-more__control"})

       
        reviews_list = [] # list of reviews
        reviews_status = [] # list of comments (good or bad)
        for reviews in soup_result:
            if reviews.string:
                reviews_list.append(reviews.string)
                # passing the review to our model
                movie_review_list = np.array([reviews.string])
                # movie_vector = vectorizer.transform(movie_review_list)
                # pred = clf.predict(movie_vector)
                # reviews_status.append('Positive' if pred else 'Negative')
        print(movie_review_list)

        
# converting list of string to list (eg. "["abc","def"]" to ["abc","def"])
def convert_to_list(my_list):
    my_list = my_list.split('","')
    my_list[0] = my_list[0].replace('["','')
    my_list[-1] = my_list[-1].replace('"]','')
    return my_list

# convert list of numbers to list (eg. "[1,2,3]" to [1,2,3])
def convert_to_list_num(my_list):
    my_list = my_list.split(',')
    my_list[0] = my_list[0].replace("[","")
    my_list[-1] = my_list[-1].replace("]","")
    return my_list
