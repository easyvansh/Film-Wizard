import streamlit as st
import pandas as pd
import joblib
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from imdb_id import *
# Set App Config

st.set_page_config(page_title="Film Wizard",
                   page_icon="https://em-content.zobj.net/thumbs/160/google/350/movie-camera_1f3a5.png", layout="wide",
                   initial_sidebar_state="collapsed",
                   menu_items={
                       'About': "# This is a header. This is an *extremely* cool app!"
                   })
# st.markdown(f"""
#             <style>
#             .stApp {{background-image: url("");
#                      background-attachment: fixed;
#                      base: light;
#                      background-size: cover}}
#          </style>
#          """, unsafe_allow_html=True)

with open('./styles.css') as f:
    css = f.read()

st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)

st.title("Film Wizard")


# Load models and MovieDB
df = joblib.load('models/movie_db.df')
tfidf_matrix = joblib.load('models/tfidf_mat.tf')
tfidf = joblib.load('models/vectorizer.tf')
cos_mat = joblib.load('models/cos_mat.mt')


def fetch_poster(movie_id):
    response = requests.get(
        'https://api.themoviedb.org/3/movie/{}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US'.format(movie_id))
    data = response.json()
    return "https://image.tmdb.org/t/p/original/" + data['poster_path']

# define functions


def get_recommendations(movie, n=5):

    # get index from dataframe
    index = df[df['title'] == movie].index[0]

    # sort top n similar movies
    similar_movies = sorted(
        list(enumerate(cos_mat[index])), reverse=True, key=lambda x: x[1])

    # extract names from dataframe and return movie names
    recommendation = []
    posters = []

    ids = []
    for movie in movies:
        _id = generate_id(name=movie)
        ids.append(_id)
    for i in similar_movies[1:n+1]:
        recommendation.append(df.iloc[i[0]].title)
        posters.append(fetch_poster(df.iloc[i[0]].id))

    return [recommendation, posters, ids]


def get_keywords_recommendations(keywords, n=5):

    keywords = keywords.split()
    keywords = " ".join(keywords)

    # transform the string to vector representation
    key_tfidf = tfidf.transform([keywords])

    # compute cosine similarity
    result = cosine_similarity(key_tfidf, tfidf_matrix)

    # sort top n similar movies
    similar_key_movies = sorted(
        list(enumerate(result[0])), reverse=True, key=lambda x: x[1])

    # extract names from dataframe and return movie names
    recomm = []
    for i in similar_key_movies[1:n+1]:
        recomm.append(df.iloc[i[0]].title)

    return recomm


movies = []
posters = []
with st.sidebar:
    st.header("Get Recommendations by 👇")
    search_type = st.radio("", ('Movie Title', 'Keywords'))
    st.header("Source Code 📦")
    st.markdown(
        "[GitHub Repository](https://github.com/easyvansh/Film-Wizard)")


# call functions based on selectbox
if search_type == 'Movie Title':
    st.subheader("Select Movie 🎬")

    movie_name = st.selectbox('', df.title)
    if st.button('Recommend 🚀'):
        with st.spinner('Wait for it...'):
            movies = get_recommendations(movie_name)[0]
            posters = get_recommendations(movie_name)[1]
            ids = get_recommendations(movie_name)[2]
else:
    st.subheader('Enter Cast / Crew / Tags / Genre  🌟')
    keyword = st.text_input('', 'Christopher Nolan')
    if st.button('Recommend 🚀'):
        with st.spinner('Wait for it...'):
            movies = get_keywords_recommendations(keyword)


# display posters
if movies:
    col1, col2, col3,col4, col5= st.columns(5, gap='medium')
    with col1:
        st.markdown(f'''<h3>{movies[0]}</h3><a href="{ids[0]}"><img src="{posters[0]}" width="100%"  /></a>''' ,unsafe_allow_html=True)
        
    with col2:
        st.markdown(f'''<h3>{movies[1]}</h3><a href="{ids[1]}"><img src="{posters[1]}" width="100%"  /></a>''' ,unsafe_allow_html=True)

    with col3:
        st.markdown(f'''<h3>{movies[2]}</h3><a href="{ids[2]}"><img src="{posters[2]}" width="100%"  /></a>''' ,unsafe_allow_html=True)

    with col4:
        st.markdown(f'''<h3>{movies[3]}</h3><a href="{ids[3]}"><img src="{posters[3]}" width="100%"  /></a>''' ,unsafe_allow_html=True)
       
    with col5:
        st.markdown(f'''<h3>{movies[4]}</h3><a href="{ids[4]}"><img src="{posters[4]}" width="100%"  /></a>''' ,unsafe_allow_html=True)
        
