import os, base64, math
from io import BytesIO
from flask import Flask, request, redirect, render_template, jsonify, abort, g
import requests
from urllib.parse import quote
import pandas as pd
from pandas.plotting import scatter_matrix
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import numpy as np
import json

from spotify_analysis import app
# from spotify_analysis.views import check_token

# Spotify URLS
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

# Set directory name if running on flask or gunicorn
dirname = os.getcwd().split('\\')[-1]
url_prefix = "spotify_analysis/" if os.path.isdir("spotify_analysis") else ""

# Unused Currently
# def plot_corr(df, size=10):
#     '''Function plots a graphical correlation matrix for each pair of columns in the dataframe.

#     Arguments:
#         df -- pandas DataFrame
#         size -- vertical and horizontal size of the plot'''
#     corr = df.corr()
#     fig, ax = plt.subplots(figsize=(size, size))
#     ax.matshow(corr)
#     plt.xticks(range(len(corr.columns)), corr.columns);
#     plt.yticks(range(len(corr.columns)), corr.columns);
#     return plt

def get_png(fig):
    """Returns a matplotlib figure as a base64 encoded png
    
    Arguments:
    fig -- the figure to save and encode
    """
    png_output = BytesIO()
    fig.savefig(png_output, format='png', transparent=True)
    png_output.seek(0)
    figdata_png = base64.b64encode(png_output.getvalue()).decode('ascii')
    plt.clf()
    return(figdata_png)

@app.route("/api/data/<filename>")
def data_view(filename):
    """Returns an array of base 64 encoded png files,
    box plots and histograms for each column except name
    
    Arguments:
    filename -- the file to get the data from
    """
    url = "./" + url_prefix + "data/" + filename
    df = pd.read_pickle(url).drop(columns=['name','analysis_url', 'id', 'track_href', 'type', 'uri'])
    df = df.drop(columns = ['duration_ms', 'key', 'mode', 'time_signature'])
    
    figures = []
    for col in df.columns:
        fig = df[col].astype(float).sort_values().plot(kind = 'box', legend=True, color='#5f0000').get_figure()
        figures.append(get_png(fig))
        fig = df[col].astype(float).sort_values().plot(kind = 'hist', legend=True, color='#5f0000').get_figure()
        figures.append(get_png(fig))

    # fig = plot_corr(df, size=11).gcf()
    # figures.append(get_png(fig))
    return jsonify({'figures': figures})

def load_songs(url, limit = 100):
    """Helper method for loading songs and their data from a Spotify playlist
    Returns the list of songs
    
    Arguments:
    url -- the playlist's Spotify API url
    limit -- the number of songs to request at once, default 100 (Spotify's playlist max)
    """
    access_token = request.cookies.get('token')
    header = {"Authorization": "Bearer {}".format(access_token)}
    
    params = {
        "limit" : limit,
        "offset" : 0
    }

    songs = []
    while True:
        songs_response = requests.get(url, headers=header, params=params)
        try:
            songs_data = songs_response.json()
        except Exception as e:
            return (songs_response.content, songs_response.status_code, songs_response.headers.items())
        
        # Query API for audio features
        if songs_data and "items" in songs_data and len(songs_data["items"]) >= 1:
            song_api_endpoint = "{}/audio-features".format(SPOTIFY_API_URL)
            song_ids = ",".join([song["track"]["id"] for song in songs_data["items"] if song["track"]["id"] is not None])
            song_response = requests.get(song_api_endpoint, headers=header, params={"ids" : song_ids})
            song_data = song_response.json()['audio_features']

            for (song, features) in zip(songs_data["items"], song_data):
                features.update( {"name" : song["track"]["name"], "popularity" : song["track"]["popularity"]} )

            songs.extend(song_data)
        else:
            # Finished querying playlist
            break
        params["offset"] += limit;  

    return songs

@app.route("/api/load/", methods=['POST'])
def data_grab(playlist_url = None, name = "song_data"):
    """POST endpoint for loading song data

    Arguments:
    playlist_url -- the playlist to get the songs from, default none, which represents saved songs
    name -- the name of file to save the data to, default song_data
    """
    if not request.get_json():
        abort(400)

    params = request.get_json()

    if params['url']:
        # Load from playlist
        playlist_url = params['url']
        limit = 100
        playlist_url = playlist_url.replace("spotify:user:", "users/").replace(":playlist:", "/playlists/")
        songs_api_endpoint = "{}/{}/tracks".format(SPOTIFY_API_URL, playlist_url)
    else:
        # Load from saved
        limit = 50
        songs_api_endpoint = "{}/me/tracks".format(SPOTIFY_API_URL)
    
    # Load songs and drop columns that contain unique and unused information 
    songs = load_songs(songs_api_endpoint, limit)
    if len(songs) > 0:
        df = pd.DataFrame(songs)#.drop(columns=['analysis_url', 'id', 'track_href', 'type', 'uri'])
    else:
        return jsonify({'success': False, "url" : None})
    
    if params['name']:
        name = params['name']

    file_url = "./" + url_prefix + "data/" + name + ".pkl"
    df.to_pickle(file_url)
    return jsonify({'success': True, "url" : file_url})

@app.route("/api/learn/")
@app.route("/api/learn/<name>")
def data_learn(name = "song_data"):
    """GET endpoint for training model

    Arguments:
    name -- the name of file to get the data from, default song_data
    """
    # load data
    df = pd.read_pickle("./" + url_prefix + "data/" + name + ".pkl").drop(columns=['analysis_url', 'id', 'track_href', 'type', 'uri'])

    # drop "useless" columns
    df = df.drop(columns = ['duration_ms', 'key', 'mode', 'time_signature'])

    # split data into train and test sets
    X_train, X_test, y_train, y_test = train_test_split(df.drop('name',axis=1), df['name'], test_size=0.30)

    # fit estimator
    #clf = IsolationForest(n_estimators = 500, contamination = 0.11)
    
    clf = make_pipeline(StandardScaler(), OneClassSVM(nu = 0.11, gamma=0.04))
    clf.fit(X_train, y_train)

    # Predict off test data and create array of outliers 
    predictions = clf.predict(X_test)
    outliers = [name for name, predict in zip(y_test, predictions) if predict < 0]
    count = len(outliers)
    
    with open("./" + url_prefix + "model/" + "clf.pkl", 'wb') as fid:
        pickle.dump(clf, fid, 2) 

    return jsonify({'success': True, "test_outliers": json.loads(df.loc[df['name'].isin(outliers)].to_json(orient='index')), "test_outliers_count": count, "test_outliers_%": count/len(y_test)*100})

@app.route("/api/predict/", methods=['POST'])
def predict(url = "song_data"):
    """POST endpoint for training model

    Arguments:
    url -- the name of file or playlist spotify URI to get the data from, default song_data
    """
    if not request.get_json():
        abort(400)

    params = request.get_json()
    url = params['url']
    
    if "spotify:user:" in url:
        # Load songs from playlist
        url = url.replace("spotify:user:", "users/").replace(":playlist:", "/playlists/")
        songs_api_endpoint = "{}/{}/tracks".format(SPOTIFY_API_URL, url)
        songs = load_songs(songs_api_endpoint, 100)
        df = pd.DataFrame(songs).drop(columns=['analysis_url', 'id', 'track_href', 'type', 'uri'])
        df.dropna(inplace=True)
    else:
        # Load songs from saved data
        try:
            df = pd.read_pickle("./" + url_prefix + "data/" + url + ".pkl")
        except Exception as e:
            return jsonify({'success': False})    
    
    # Open model and predict
    try:
        pkl_file = open("./" + url_prefix + "model/" + "clf.pkl", 'rb')
    except Exception as e:
        return jsonify({'success': False})
    
    clf = pickle.load(pkl_file)
    df = df.drop(columns = ['duration_ms', 'key', 'mode', 'time_signature'])
    predictions = clf.predict(df.drop(columns=['name', 'analysis_url', 'id', 'track_href', 'type', 'uri']))
    y = df['name']
    inliers = [name for name, predict in zip(y, predictions) if predict > 0]
    outliers = [name for name, predict in zip(y, predictions) if predict < 0]
    count = len(inliers)

    with open("./" + url_prefix + "model/" + url  +  "_inliers.pkl", 'wb') as fid:
        pickle.dump(df.loc[df['name'].isin(inliers)], fid, 2)

    return jsonify({'success': True, "inliers": json.loads(df.loc[df['name'].isin(inliers)].to_json(orient='index')), "inliers_count" : count ,"inliers_%" : count/len(y)*100})

@app.route("/api/save/", methods=['POST'])
def save(name = "song_data"):
    """POST endpoint for saving playlist

    Arguments:
    name -- the name of the playlist to save the inliers of 
    """
    access_token = request.cookies.get('token')
    headers = {"Authorization": "Bearer {}".format(access_token), "Content-Type" : "application/json"}

    if not request.get_json():
        abort(400)

    params = request.get_json()
    name = params['url']
    
    # Load songs from saved data
    try:
        df = pd.read_pickle("./" + url_prefix + "model/" + name + "_inliers.pkl")
    except Exception as e:
        return jsonify({'success': False}, {'error': repr(e)})    

    # Convert data to list of lists with a max length of 100 (Spotify's limit)
    uris = []
    length = math.ceil(df.shape[0] / 100)
    for i in range(length):
        uris.append(df[100*i:(100 * i) + 100]['uri'])
    
    # Get current user's ID
    user_api_endpoint = "{}/me".format(SPOTIFY_API_URL)
    user_response = requests.get(user_api_endpoint, headers=headers)
    user_data = user_response.json()
    user_id = user_data['id']

    # Create the playlist
    playlist_api_endpoint = "{}/users/{}/playlists".format(SPOTIFY_API_URL, user_id)

    data = {'name': name.title() + " Inliers", 'public': False}
    playlist_response = requests.post(playlist_api_endpoint, headers=headers, data=json.dumps(data))
    try:
        playlist_data = playlist_response.json()
        playlist_id = playlist_data['id']
    except Exception as e:
        return (playlist_response.content, playlist_response.status_code, playlist_response.headers.items())
    
    # Save songs to the playlist
    playlist_api_endpoint = playlist_api_endpoint + "/{}/tracks".format(playlist_id)
    
    for uri in uris:
        data = {'uris': uri.tolist()}
        playlist_response = requests.post(playlist_api_endpoint, headers=headers, data=json.dumps(data))
        if playlist_response.status_code != 201:
            return (playlist_response.content, playlist_response.status_code, playlist_response.headers.items())


    return jsonify({'success': True})
