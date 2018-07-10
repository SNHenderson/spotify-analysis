import os, base64
from io import BytesIO
from flask import Flask, request, redirect, render_template, jsonify, abort
import requests
from urllib.parse import quote
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import pickle
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import IsolationForest
import numpy as np
import json

from spotify_analysis import app
from spotify_analysis.views import check_token

# Spotify URLS
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

dirname = os.getcwd().split('\\')[-1]
url_prefix = "spotify_analysis/" if os.path.isdir("spotify_analysis") else ""

# Unused Currently
# def plot_corr(df, size=10):
#     '''Function plots a graphical correlation matrix for each pair of columns in the dataframe.

#     Input:
#         df: pandas DataFrame
#         size: vertical and horizontal size of the plot'''
#     corr = df.corr()
#     fig, ax = plt.subplots(figsize=(size, size))
#     ax.matshow(corr)
#     plt.xticks(range(len(corr.columns)), corr.columns);
#     plt.yticks(range(len(corr.columns)), corr.columns);
#     return plt

def get_png(fig):
    png_output = BytesIO()
    fig.savefig(png_output, format='png', transparent=True)
    png_output.seek(0)
    figdata_png = base64.b64encode(png_output.getvalue()).decode('ascii')
    plt.clf()
    return(figdata_png)

@app.route("/api/data/<filename>")
def data_view(filename):
    check_token()
    url = "./" + url_prefix + "data/" + filename
    df = pd.read_pickle(url)
    figures = []
    for col in df.columns:
        if(col != 'name'):
            fig = df[col].astype(float).sort_values().plot(kind = 'box', legend=True, color='#025f67').get_figure()
            figures.append(get_png(fig))
            fig = df[col].astype(float).sort_values().plot(kind = 'hist', legend=True, color='#025f67').get_figure()
            figures.append(get_png(fig))

    # fig = plot_corr(df, size=11).gcf()
    # figures.append(get_png(fig))
    return jsonify({'figures': figures})

def load_songs(url, limit):
    check_token()
    pkl_file = open('./' + url_prefix + 'auth/header.pkl', 'rb')
    header = pickle.load(pkl_file)
    
    params = {
        "limit" : limit,
        "offset" : 0
    }

    songs = []
    while True:
        songs_response = requests.get(url, headers=header, params=params)
        songs_data = songs_response.json()
        if songs_data and "items" in songs_data and len(songs_data["items"]) >= 1:
            song_api_endpoint = "{}/audio-features".format(SPOTIFY_API_URL)
            song_ids = ",".join([song["track"]["id"] for song in songs_data["items"] if song["track"]["id"] is not None])
            song_response = requests.get(song_api_endpoint, headers=header, params={"ids" : song_ids})
            song_data = song_response.json()['audio_features']

            for (song, features) in zip(songs_data["items"], song_data):
                features.update( {"name" : song["track"]["name"], "popularity" : song["track"]["popularity"]} )

            songs.extend(song_data)
        else:
            break
        params["offset"] += limit;  

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
    df.to_pickle("./" + url_prefix + "data/" + name + ".pkl")
    return jsonify({'Success': True})

@app.route("/api/learn/")
@app.route("/api/learn/<name>")
def data_learn(name = "song_data"):
    df = pd.read_pickle("./" + url_prefix + "data/" + name + ".pkl")

    X_train, X_test, y_train, y_test = train_test_split(df.drop('name',axis=1), df['name'], test_size=0.30)

    param_grid = { 
        'n_estimators': [100, 300],
        'max_features': [1.0, 0.5],
        'max_samples': ['auto', 0.5]
    }

    CV_clf = GridSearchCV(estimator=IsolationForest(), param_grid=param_grid, scoring="accuracy")
    CV_clf.fit(X_train, y_train)
    clf = IsolationForest(n_estimators = CV_clf.best_params_['n_estimators'], max_features = CV_clf.best_params_['max_features'], max_samples = CV_clf.best_params_['max_samples'])
    clf.fit(X_train, y_train)

    predictions = clf.predict(X_test)
    unmatch = [name for name, predict in zip(y_test, predictions) if predict < 0]
    count = len(unmatch)
    
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

    playlist_url = params['url']
    
    if "spotify:user:" in playlist_url:
        playlist_url = playlist_url.replace("spotify:user:", "users/").replace(":playlist:", "/playlists/")
        songs_api_endpoint = "{}/{}/tracks".format(SPOTIFY_API_URL, playlist_url)
        songs = load_songs(songs_api_endpoint, 100)
        df = pd.DataFrame(songs).drop(columns=['analysis_url', 'id', 'track_href', 'type', 'uri'])
        df.dropna(inplace=True)
    else:
        pkl_file = open("./" + url_prefix + "data/" + playlist_url + ".pkl", 'rb')
        df = pickle.load(pkl_file)
    
    pkl_file = open('clf.pkl', 'rb')
    clf = pickle.load(pkl_file)
    predictions = clf.predict(df.drop('name', axis=1))
    y = df['name']
    match = [name for name, predict in zip(y, predictions) if predict > 0]
    unmatch = [name for name, predict in zip(y, predictions) if predict < 0]
    count = len(match)

    return jsonify({'Success': True, "Matched songs": json.loads(df.loc[df['name'].isin(match)].to_json(orient='index')), "Misclassified" : count ,"Misclassified %" : count/len(y)*100})
