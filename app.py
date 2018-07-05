import os, time, base64, errno
from threading import Thread
from io import BytesIO
from flask import Flask, request, redirect, g, render_template, jsonify
import requests
from urllib.parse import quote
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest
import numpy as np
import json

# Authentication Steps, paramaters, and responses are defined at https://developer.spotify.com/web-api/authorization-guide/
# Visit this url to see all the steps, parameters, and expected response.


app = Flask(__name__)

#  Client Keys
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')

# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

# Server-side Parameters
CLIENT_SIDE_URL = os.getenv('HEROKU_URL')
REDIRECT_URI = "{}/callback/q".format(CLIENT_SIDE_URL)
# CLIENT_SIDE_URL = "http://127.0.0.1"
# PORT = 8080
# REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)

SCOPE = "user-library-read playlist-read-private playlist-read-collaborative"
STATE = ""
SHOW_DIALOG_bool = True
SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()

auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    # "state": STATE,
    # "show_dialog": SHOW_DIALOG_str,
    "client_id": CLIENT_ID
}

AUTH_HEADER = ""

@app.route("/")
def index():
    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    # Auth Step 1: Authorization
    url_args = "&".join(["{}={}".format(key, quote(val)) for key, val in auth_query_parameters.items()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    print(auth_url)
    return redirect(auth_url)


@app.route("/callback/q")
def callback():
    # Auth Step 4: Requests refresh and access tokens
    auth_token = request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload)

    # Auth Step 5: Tokens are Returned to Application
    response_data = post_request.json()
    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]
    token_type = response_data["token_type"]
    expires_in = response_data["expires_in"]
    expire = {'expires':time.time() + expires_in, 'refresh':refresh_token}

    # Auth Step 6: Use the access token to access Spotify API
    AUTH_HEADER = {"Authorization": "Bearer {}".format(access_token)}

    with open('auth/header.pkl', 'wb') as fid:
        pickle.dump(AUTH_HEADER, fid, 2) 


    with open('auth/expire.pkl', 'wb') as fid:
        pickle.dump(expire, fid, 2) 
    thread = Thread(target=data_grab, kwargs={'header': AUTH_HEADER})
    thread.start()
    return render_template("auth.html")

def check_token():
    pkl_file = open('auth/expire.pkl', 'rb')
    expire = pickle.load(pkl_file)
    if time.time() < expire['expires']:
        return

    code_payload = {
        "grant_type": "refresh_token",
        "refresh_token": expire['refresh'],
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload)
    response_data = post_request.json()
    access_token = response_data["access_token"]
    
    if('refresh_token' in response_data):
        refresh_token = response_data["refresh_token"]
    else:
        refresh_token = expire['refresh']
    
    if('expires_in' in response_data):
        expires_in = response_data["expires_in"]
    else:
        expires_in = expire['expires']
    
    expire = {'expires':time.time() + expires_in, 'refresh':refresh_token}

    AUTH_HEADER = {"Authorization": "Bearer {}".format(access_token)}

    with open('auth/header.pkl', 'wb') as fid:
        pickle.dump(AUTH_HEADER, fid, 2) 

    with open('auth/expire.pkl', 'wb') as fid:
        pickle.dump(expire, fid, 2) 

def plot_corr(df, size=10):
    '''Function plots a graphical correlation matrix for each pair of columns in the dataframe.

    Input:
        df: pandas DataFrame
        size: vertical and horizontal size of the plot'''
    corr = df.corr()
    fig, ax = plt.subplots(figsize=(size, size))
    ax.matshow(corr)
    plt.xticks(range(len(corr.columns)), corr.columns);
    plt.yticks(range(len(corr.columns)), corr.columns);
    return plt

def get_png(fig):
    png_output = BytesIO()
    fig.savefig(png_output, format='png')
    png_output.seek(0)
    figdata_png = base64.b64encode(png_output.getvalue()).decode('ascii')
    plt.clf()
    return(figdata_png)

@app.route("/data/<filename>")
def data_page(filename):
    data = data_view(filename).get_json()
    return render_template('output.html', data=data)

@app.route("/api/data/<filename>")
def data_view(filename):
    check_token()
    url = "./data/" + filename
    print(url)
    df = pd.read_pickle(url)
    figures = []
    for col in df.columns:
        if(col != 'name'):
            fig = df[col].astype(float).sort_values().plot(kind = 'box', legend=True).get_figure()
            figures.append(get_png(fig))
            fig = df[col].astype(float).sort_values().plot(kind = 'hist', legend=True).get_figure()
            figures.append(get_png(fig))

    fig = plot_corr(df, size=11).gcf()
    figures.append(get_png(fig))
    return jsonify({'figures': figures})

def load_songs(url, limit):
    check_token()
    pkl_file = open('auth/header.pkl', 'rb')
    header = pickle.load(pkl_file)
    
    params = {
        "limit" : limit,
        "offset" : 0
    }

    songs = []
    while True:
        songs_response = requests.get(url, headers=header, params=params)
        songs_data = songs_response.json()
        if songs_data and "items" in songs_data:
            if len(songs_data["items"]) < 1:
                print("Finished parsing songs")
                break

            song_api_endpoint = "{}/audio-features".format(SPOTIFY_API_URL)
            song_ids = ",".join([song["track"]["id"] for song in songs_data["items"] if song["track"]["id"] is not None])
            song_response = requests.get(song_api_endpoint, headers=header, params={"ids" : song_ids})
            song_data = song_response.json()['audio_features']

            for (song, features) in zip(songs_data["items"], song_data):
                features.update( {"name" : song["track"]["name"], "popularity" : song["track"]["popularity"]} )

            songs.extend(song_data)
        else:
            print("Error:", songs_data)
            break    
        params["offset"] += limit;  
        print("Loaded ", params["offset"], " songs")

    return songs

@app.route("/api/load/", methods=['POST'])
def data_grab(playlist_url = None, name = "song_data"):
    if not request.get_json():
        abort(400)

    params = request.get_json()

    if params['url']:
        playlist_url = params['url']
        limit = 100
        playlist_url = playlist_url.replace("spotify:user:", "users/").replace(":playlist:", "/playlists/")
        songs_api_endpoint = "{}/{}/tracks".format(SPOTIFY_API_URL, playlist_url)
    else:
        limit = 50
        songs_api_endpoint = "{}/me/tracks".format(SPOTIFY_API_URL)
    
    songs = load_songs(songs_api_endpoint, limit)

    df = pd.DataFrame(songs).drop(columns=['analysis_url', 'id', 'track_href', 'type', 'uri'])

    if params['name']:
        name = params['name']

    df.to_pickle("./data/" + name + ".pkl")
    return jsonify({'Success': True})

@app.route("/api/learn/")
@app.route("/api/learn/<name>")
def data_learn(name = "song_data"):
    df = pd.read_pickle("./data/" + name + ".pkl")
    #print("Splitting data")
    X_train, X_test, y_train, y_test = train_test_split(df.drop('name',axis=1), df['name'], test_size=0.30)
    clf = IsolationForest(contamination=0.1)
    #print("Fitting data")
    clf.fit(X_train, y_train)

    predictions = clf.predict(X_test)

    unmatch = [name for name, predict in zip(y_test, predictions) if predict < 0]
    #print("Mismatched songs: \n", df.loc[df['name'].isin(unmatch)])
    
    count = len(unmatch)

    #print("{}/{} misclassified: {:3f}%".format(count, len(y_test), (count/len(y_test)*100)))
    #print(df.loc[df['name'].isin(unmatch)].describe())
    
    with open('clf.pkl', 'wb') as fid:
        pickle.dump(clf, fid, 2) 
    return jsonify({'Success': True, "Test mismatched %": count/len(y_test)*100})

@app.route("/api/predict/", methods=['POST'])
def predict():
    if not request.get_json():
        abort(400)

    params = request.get_json()
    if not params['url']:
        abort(404)

    playlist_url = params['url'].replace("spotify:user:", "users/").replace(":playlist:", "/playlists/")

    songs_api_endpoint = "{}/{}/tracks".format(SPOTIFY_API_URL, playlist_url)
    songs = load_songs(songs_api_endpoint, 100)

    df = pd.DataFrame(songs).drop(columns=['analysis_url', 'id', 'track_href', 'type', 'uri'])
    # 'key', 'mode', 'time_signature'
    df.dropna(inplace=True)
    
    pkl_file = open('clf.pkl', 'rb')
    clf = pickle.load(pkl_file)
    predictions = clf.predict(df.drop('name', axis=1))
    
    y = df['name']
    match = [name for name, predict in zip(y, predictions) if predict > 0]
    print("Matched songs: \n", df.loc[df['name'].isin(match)])

    unmatch = [name for name, predict in zip(y, predictions) if predict < 0]
    
    count = len(match)

    #print("{}/{} misclassified: {:3f}%".format(count, len(y), (count/len(y)*100)))
    #print("Matched: \n", df.loc[df['name'].isin(match)].describe())
    #print("Unmatched: \n", df.loc[df['name'].isin(unmatch)].describe())    
    return jsonify({'Success': True, "Matched songs": json.loads(df.loc[df['name'].isin(match)].to_json(orient='index')), "Misclassified" : count ,"Misclassified %" : count/len(y)*100})

if __name__ == "__main__":
    app.run(debug=True, port=PORT)
