import streamlit as st
from PIL import Image
import json
from Classifier import KNearestNeighbours
from bs4 import BeautifulSoup
import requests, io
import PIL.Image
import urllib.parse

API_KEY = "9f2854c7ba4c480b80063b25b0db90f9"
hdr = {'User-Agent': 'Mozilla/5.0'}

# ---------------- Load Data ----------------
with open('./Data/movie_data.json', 'r+', encoding='utf-8') as f:
    data = json.load(f)
with open('./Data/movie_titles.json', 'r+', encoding='utf-8') as f:
    movie_titles = json.load(f)

    st.markdown("""
<style>

/* Main app background */
[data-testid="stAppViewContainer"] {
    background-color: #000000;
}

</style>
""", unsafe_allow_html=True)

# ---------------- Functions ----------------
def movie_poster_fetcher(poster_url):
    """Display Poster from URL"""
    if poster_url:
        try:
            response = requests.get(poster_url)
            image = PIL.Image.open(io.BytesIO(response.content))
            image = image.resize((158, 301))
            st.image(image, use_container_width=False)
        except:
            st.write("Could not fetch poster")
    else:
        st.write("Poster not available")

def fetch_movie_details(movie_name, imdb_link=None):
    """Fetch poster, overview, rating, release. Try TMDb, fallback IMDb"""
    movie_name_encoded = urllib.parse.quote(movie_name)
    tmdb_url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={movie_name_encoded}"

    try:
        response = requests.get(tmdb_url)
        data_tmdb = response.json()
        if 'results' in data_tmdb and len(data_tmdb['results']) > 0:
            result = data_tmdb['results'][0]
            poster_path = result.get('poster_path')
            overview = result.get('overview', "No description available")
            rating = result.get('vote_average', "N/A")
            release = result.get('release_date', "N/A")
            poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
            return poster, overview, rating, release
    except Exception as e:
        print("TMDb API error:", e)

    if imdb_link:
        try:
            url_data = requests.get(imdb_link, headers=hdr).text
            s_data = BeautifulSoup(url_data, 'html.parser')

            imdb_dp = s_data.find("meta", property="og:image")
            poster = imdb_dp.attrs['content'] if imdb_dp else None

            imdb_descr = s_data.find("meta", property="og:description")
            overview = imdb_descr.attrs['content'] if imdb_descr else "No description available"

            rating_span = s_data.find("span", itemprop="ratingValue")
            rating = rating_span.text if rating_span else "N/A"

            release_span = s_data.find("meta", itemprop="datePublished")
            release = release_span.attrs['content'] if release_span else "N/A"

            return poster, overview, rating, release
        except Exception as e:
            print("IMDb scraping error:", e)

    return None, "No description available", "N/A", "N/A"

def KNN_Movie_Recommender(test_point, k):
    """Return top-k recommended movies"""
    target = [0 for item in movie_titles]
    model = KNearestNeighbours(data, target, test_point, k=k)
    model.fit()
    table = []
    for i in model.indices:
        table.append([movie_titles[i][0], movie_titles[i][2], data[i][-1]])  # title, imdb_link, original IMDb rating
    return table

# ---------------- Streamlit App ----------------
st.set_page_config(page_title="Movie Recommendation System", layout="wide")

def run():
    # Logo
    img1 = Image.open('./meta/logo.png').resize((800, 400))
    st.image(img1, use_container_width=False)

    st.title("Movie Recommendation System")
    st.markdown('<h4 style="color:#d73b5c;">* Data is based "IMDB 5000 Movie Dataset"</h4>',
                unsafe_allow_html=True)

    genres = ['Action', 'Adventure', 'Animation', 'Biography', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Family',
              'Fantasy', 'Film-Noir', 'Game-Show', 'History', 'Horror', 'Music', 'Musical', 'Mystery', 'News',
              'Reality-TV', 'Romance', 'Sci-Fi', 'Short', 'Sport', 'Thriller', 'War', 'Western']
    movies = [title[0] for title in movie_titles]
    category = ['--Select--', 'Movie based', 'Genre based']
    cat_op = st.selectbox('Select Recommendation Type', category)

    if cat_op == category[0]:
        st.warning('Please select Recommendation Type!!')

    # ---------------- Movie Based ----------------
    elif cat_op == category[1]:
        col1, col2 = st.columns(2)
        with col1:
            search_movie = st.text_input("Search for a movie (type name and press Enter):")
        with col2:
            select_movie = st.selectbox('Or select a movie:', ['--Select--'] + movies, index=0)

        movie_to_use = search_movie.strip() if search_movie.strip() else (select_movie if select_movie != '--Select--' else None)
        fetch_posters = st.radio("Want to Fetch Movie Poster?", ('Yes', 'No'))

        if movie_to_use:
            no_of_reco = st.slider('Number of movies you want Recommended:', 5, 20, 5)

            if movie_to_use in movies:
                selected_index = movies.index(movie_to_use)
                selected_imdb_link = movie_titles[selected_index][2]
                selected_rating = data[selected_index][-1]
            else:
                selected_index = None
                selected_imdb_link = None
                selected_rating = "N/A"

            # Selected movie details
            poster, overview, tmdb_rating, release = fetch_movie_details(movie_to_use, selected_imdb_link)
            st.markdown(f"### Selected Movie: {movie_to_use}")
            if fetch_posters == 'Yes':
                movie_poster_fetcher(poster)
            st.markdown(f"**Overview:** {overview}")
            st.markdown(f"**TMDb Rating:** {tmdb_rating} ⭐")
            st.markdown(f"**Release Date:** {release}")
            st.markdown(f"**Original IMDb Rating:** {selected_rating} ⭐")
            st.markdown("---")

            # ---------------- KNN Recommendations Horizontal ----------------
            if selected_index is not None:
                test_points = data[selected_index]
                table = KNN_Movie_Recommender(test_points, no_of_reco + 1)
                table = [x for x in table if x[0] != movie_to_use]  # exclude selected movie

                st.success('Recommended Movies:')
                # Show 5 per row
                row_size = 5
                for i in range(0, len(table), row_size):
                    row = table[i:i+row_size]
                    cols = st.columns(len(row))
                    for col, (movie, imdb_link, orig_rating) in zip(cols, row):
                        with col:
                            poster, overview, tmdb_rating, release = fetch_movie_details(movie, imdb_link)
                            st.markdown(f"**[{movie}]({imdb_link})**")
                            if fetch_posters == 'Yes':
                                st.image(poster, use_container_width=True)
                            st.markdown(f"<b>TMDb:</b> {tmdb_rating} ⭐", unsafe_allow_html=True)
                            st.markdown(f"<b>IMDb:</b> {orig_rating} ⭐", unsafe_allow_html=True)
                            st.markdown(f"<b>Release:</b> {release}", unsafe_allow_html=True)
                            st.markdown(f"<p style='text-align:justify;'>{overview}</p>", unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)

    # ---------------- Genre Based ----------------
    elif cat_op == category[2]:
        sel_gen = st.multiselect('Select Genres:', genres)
        fetch_posters = st.radio("Want to Fetch Movie Poster?", ('Yes', 'No'))

        if sel_gen:
            imdb_score = st.slider('Choose IMDb score:', 1, 10, 8)
            no_of_reco = st.number_input('Number of movies:', 5, 20, 5)
            test_point = [1 if genre in sel_gen else 0 for genre in genres]
            test_point.append(imdb_score)
            table = KNN_Movie_Recommender(test_point, no_of_reco)

            st.success('Recommended Movies:')
            row_size = 5
            for i in range(0, len(table), row_size):
                row = table[i:i+row_size]
                cols = st.columns(len(row))
                for col, (movie, imdb_link, orig_rating) in zip(cols, row):
                    with col:
                        poster, overview, tmdb_rating, release = fetch_movie_details(movie, imdb_link)
                        st.markdown(f'<div style="background-color:#1f1f1f; padding:10px; border-radius:10px; text-align:center; height:500px; overflow:hidden;">', unsafe_allow_html=True)
                        st.markdown(f'<h4 style="color:#d73b5c;">[{movie}]({imdb_link})</h4>', unsafe_allow_html=True)
                        if fetch_posters == 'Yes' and poster:
                            st.image(poster, use_column_width=True)
                        st.markdown(f"<b>TMDb:</b> {tmdb_rating} ⭐", unsafe_allow_html=True)
                        st.markdown(f"<b>IMDb:</b> {orig_rating} ⭐", unsafe_allow_html=True)
                        st.markdown(f"<b>Release:</b> {release}", unsafe_allow_html=True)
                        st.markdown(f"<p style='text-align:justify;'>{overview}</p>", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    run()