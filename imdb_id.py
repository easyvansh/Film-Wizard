from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup


def get_with_ssl_fallback(url, **kwargs):
    try:
        return requests.get(url, **kwargs)
    except requests.exceptions.SSLError:
        return requests.get(url, verify=False, **kwargs)


def generate_id(name):
    assert isinstance(name, str)

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Referer": "https://www.imdb.com/",
    }
    search_url = (
        "https://www.imdb.com/find/"
        f"?q={quote_plus(name)}&s=tt&exact=true&ref_=fn_tt_ex"
    )

    response = get_with_ssl_fallback(search_url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    result_link = soup.select_one(
        'section[data-testid="find-results-section-title"] a[href^="/title/tt"]'
    )

    if result_link is None:
        return "https://www.imdb.com/"

    title_id = result_link["href"].split("/")[2]
    return f"https://www.imdb.com/title/{title_id}/"
