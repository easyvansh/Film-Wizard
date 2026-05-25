import os
import re
from html import escape
from urllib.parse import quote

import joblib
import requests
import streamlit as st
import urllib3
from bs4 import BeautifulSoup
from sklearn.metrics.pairwise import cosine_similarity

from imdb_id import generate_id


TMDB_API_KEY = os.getenv("TMDB_API_KEY", "8265bd1679663a7ea12ac168da84d2e8")
POSTER_PLACEHOLDER = "https://placehold.co/500x750/14161f/f5c84b?text=No+Poster"
REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.imdb.com/",
}
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_with_ssl_fallback(url, **kwargs):
    try:
        return requests.get(url, **kwargs)
    except requests.exceptions.SSLError:
        return requests.get(url, verify=False, **kwargs)


st.set_page_config(
    page_title="Film Wizard",
    page_icon=":movie_camera:",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Film Wizard recommends movies using TF-IDF and cosine similarity.",
    },
)


@st.cache_resource(show_spinner=False)
def load_artifacts():
    return {
        "df": joblib.load("models/movie_db.df"),
        "tfidf_matrix": joblib.load("models/tfidf_mat.tf"),
        "tfidf": joblib.load("models/vectorizer.tf"),
        "cos_mat": joblib.load("models/cos_mat.mt"),
    }


@st.cache_data(show_spinner=False)
def fetch_movie_assets(movie_id, movie_title):
    poster_path = None
    imdb_id = None
    movie_url = f"https://www.themoviedb.org/movie/{movie_id}"

    try:
        response = get_with_ssl_fallback(
            f"https://api.themoviedb.org/3/movie/{movie_id}",
            params={"api_key": TMDB_API_KEY, "language": "en-US"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        data = {}

    poster_path = data.get("poster_path")
    imdb_id = data.get("imdb_id")
    if not poster_path:
        poster_path = search_poster_path(movie_title)

    if imdb_id:
        movie_url = f"https://www.imdb.com/title/{imdb_id}/"

    imdb_assets = {}
    if not poster_path:
        imdb_assets = fetch_imdb_assets(movie_title, imdb_id)

    poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
    if not poster_url:
        poster_url = imdb_assets.get("poster")
    if not imdb_id and imdb_assets.get("url"):
        movie_url = imdb_assets["url"]

    return {
        "poster": poster_url or POSTER_PLACEHOLDER,
        "url": movie_url,
    }


@st.cache_data(show_spinner=False)
def search_poster_path(movie_title):
    try:
        response = get_with_ssl_fallback(
            "https://api.themoviedb.org/3/search/movie",
            params={
                "api_key": TMDB_API_KEY,
                "query": movie_title,
                "include_adult": "false",
                "language": "en-US",
                "page": 1,
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    for result in response.json().get("results", []):
        poster_path = result.get("poster_path")
        if poster_path:
            return poster_path

    return None


@st.cache_data(show_spinner=False)
def fetch_imdb_assets(movie_title, imdb_id=None):
    slug = re.sub(r"[^a-z0-9]+", "_", movie_title.lower()).strip("_")
    if not slug:
        return {}

    suggestion_url = (
        f"https://v3.sg.media-imdb.com/suggestion/{slug[0]}/{quote(slug)}.json"
    )

    try:
        response = get_with_ssl_fallback(
            suggestion_url,
            headers={"Accept": "application/json", "User-Agent": REQUEST_HEADERS["User-Agent"]},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("d", [])
    except (ValueError, requests.RequestException):
        results = []

    selected = None
    if imdb_id:
        selected = next((item for item in results if item.get("id") == imdb_id), None)

    if selected is None:
        selected = next(
            (
                item
                for item in results
                if item.get("l", "").casefold() == movie_title.casefold()
                and item.get("i", {}).get("imageUrl")
            ),
            None,
        )

    if selected is None:
        selected = next(
            (item for item in results if item.get("i", {}).get("imageUrl")),
            None,
        )

    if selected:
        title_id = selected.get("id")
        return {
            "poster": selected.get("i", {}).get("imageUrl"),
            "url": f"https://www.imdb.com/title/{title_id}/" if title_id else None,
        }

    return fetch_imdb_page_assets(movie_title, imdb_id)


@st.cache_data(show_spinner=False)
def fetch_imdb_page_assets(movie_title, imdb_id=None):
    try:
        movie_url = (
            f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else generate_id(movie_title)
        )
        if "/title/tt" not in movie_url:
            return {}

        response = get_with_ssl_fallback(
            movie_url, headers=REQUEST_HEADERS, timeout=10
        )
        response.raise_for_status()
    except (AssertionError, requests.RequestException):
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    for selector in (
        'meta[property="og:image"]',
        'meta[name="twitter:image"]',
        'meta[property="twitter:image"]',
    ):
        image_meta = soup.select_one(selector)
        if image_meta and image_meta.get("content"):
            return {"poster": image_meta["content"], "url": movie_url}

    return {}


def get_title_recommendations(movie_title, n=5):
    df = artifacts["df"]
    cos_mat = artifacts["cos_mat"]

    movie_rows = df[df["title"] == movie_title]
    if movie_rows.empty:
        return []

    movie_index = movie_rows.index[0]
    similar_movies = sorted(
        enumerate(cos_mat[movie_index]), reverse=True, key=lambda item: item[1]
    )

    return build_recommendation_cards(similar_movies[1 : n + 1])


def get_keyword_recommendations(keywords, n=5):
    clean_keywords = " ".join(keywords.split())
    if not clean_keywords:
        return []

    tfidf = artifacts["tfidf"]
    tfidf_matrix = artifacts["tfidf_matrix"]

    keyword_vector = tfidf.transform([clean_keywords])
    scores = cosine_similarity(keyword_vector, tfidf_matrix)
    similar_movies = sorted(
        enumerate(scores[0]), reverse=True, key=lambda item: item[1]
    )

    return build_recommendation_cards(similar_movies[:n])


def build_recommendation_cards(scored_movies):
    df = artifacts["df"]
    cards = []

    for rank, (movie_index, score) in enumerate(scored_movies, start=1):
        movie = df.iloc[movie_index]
        title = movie["title"]
        assets = fetch_movie_assets(movie["id"], title)
        cards.append(
            {
                "rank": rank,
                "title": title,
                "score": float(score),
                "poster": assets["poster"],
                "url": assets["url"],
            }
        )

    return cards


def build_source_movie_card(movie_title):
    df = artifacts["df"]
    movie_rows = df[df["title"] == movie_title]
    if movie_rows.empty:
        return None

    movie = movie_rows.iloc[0]
    assets = fetch_movie_assets(movie["id"], movie_title)
    return {
        "title": movie_title,
        "poster": assets["poster"],
        "url": assets["url"],
    }


def render_source_movie(movie):
    if not movie:
        return

    title = escape(movie["title"])
    poster = escape(movie["poster"], quote=True)
    placeholder = escape(POSTER_PLACEHOLDER, quote=True)
    url = escape(movie["url"], quote=True)

    st.markdown(
        f"""
        <section class="source-movie">
            <div class="source-copy">
                <p class="eyebrow">Your selected movie</p>
                <h2>{title}</h2>
                <p>Recommendations below are based on this title.</p>
            </div>
            <a class="source-poster" href="{url}" target="_blank" rel="noopener noreferrer">
                <img src="{poster}" alt="{title} poster" onerror="this.onerror=null;this.src='{placeholder}';" />
            </a>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_recommendations(recommendations):
    st.markdown("### Recommended for you")

    columns = st.columns(len(recommendations), gap="large")
    for column, movie in zip(columns, recommendations):
        title = escape(movie["title"])
        poster = escape(movie["poster"], quote=True)
        placeholder = escape(POSTER_PLACEHOLDER, quote=True)
        url = escape(movie["url"], quote=True)
        with column:
            st.markdown(
                f"""
                <a class="movie-card" href="{url}" target="_blank" rel="noopener noreferrer">
                    <span class="movie-rank">#{movie['rank']}</span>
                    <img src="{poster}" alt="{title} poster" onerror="this.onerror=null;this.src='{placeholder}';" />
                    <span class="movie-title">{title}</span>
                    <span class="movie-meta">{movie['score']:.0%} similarity</span>
                </a>
                """,
                unsafe_allow_html=True,
            )


with open("styles.css", encoding="utf-8") as styles_file:
    st.markdown(f"<style>{styles_file.read()}</style>", unsafe_allow_html=True)


artifacts = load_artifacts()
df = artifacts["df"]

with st.sidebar:
    st.markdown("## Film Wizard")
    st.caption("Find your next movie from TMDB-powered recommendations.")

    search_type = st.radio(
        "Recommendation mode",
        ("Movie Title", "Keywords"),
        captions=(
            "Start from a known movie.",
            "Search by cast, crew, tags, or genre.",
        ),
    )

    result_count = st.slider("Number of recommendations", 3, 5, 5)

    st.divider()
    st.link_button(
        "View source",
        "https://github.com/easyvansh/Film-Wizard",
        use_container_width=True,
    )


st.markdown(
    """
    <section class="hero">
        <p class="eyebrow">Movie recommendation system</p>
        <h1>Film Wizard</h1>
        <p class="hero-copy">
            Pick a title you already like, or describe the kind of film you are in the mood for.
            The app compares movies with TF-IDF features and cosine similarity.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)

control_panel, stats_panel = st.columns([2.2, 1], gap="large")

with control_panel:
    with st.container(border=True):
        if search_type == "Movie Title":
            st.markdown("### Start with a movie")
            movie_name = st.selectbox(
                "Movie title",
                df["title"].sort_values(),
                index=0,
                placeholder="Choose a movie",
            )
            submitted = st.button(
                "Get recommendations",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                with st.spinner("Finding similar movies..."):
                    recommendations = get_title_recommendations(movie_name, result_count)
                    source_movie = build_source_movie_card(movie_name)
                    st.session_state["recommendations"] = recommendations
                    st.session_state["source_movie"] = source_movie
                    st.session_state["last_query"] = movie_name
                    st.session_state["last_mode"] = "Movie Title"
        else:
            st.markdown("### Search by mood or credits")
            keyword = st.text_input(
                "Keywords",
                value="Christopher Nolan",
                placeholder="Example: sci-fi space adventure Hans Zimmer",
            )
            submitted = st.button(
                "Search recommendations",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                with st.spinner("Matching keywords to movies..."):
                    recommendations = get_keyword_recommendations(keyword, result_count)
                    st.session_state["recommendations"] = recommendations
                    st.session_state["source_movie"] = None
                    st.session_state["last_query"] = keyword
                    st.session_state["last_mode"] = "Keywords"

with stats_panel:
    with st.container(border=True):
        st.metric("Movies indexed", f"{len(df):,}")
        st.metric("Recommendation modes", "2")
        st.metric("Results per search", result_count)


recommendations = st.session_state.get("recommendations", [])
source_movie = st.session_state.get("source_movie")

if recommendations:
    st.markdown(
        f'<p class="result-context">Showing results for <strong>{st.session_state.get("last_query", "")}</strong></p>',
        unsafe_allow_html=True,
    )
    render_source_movie(source_movie)
    render_recommendations(recommendations)
else:
    st.markdown(
        """
        <div class="empty-state">
            <h3>Ready when you are.</h3>
            <p>Choose a movie or enter keywords, then run a recommendation search.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
