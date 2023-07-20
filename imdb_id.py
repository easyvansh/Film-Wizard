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

    return movie_url
