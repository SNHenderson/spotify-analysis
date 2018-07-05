import requests
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest
import numpy as np
import sys
from app import check_token

# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

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

def data_grab(playlistURI = None, name = "song_data"):
    if playlistURI:
        limit = 100
        playlistURI = playlistURI.replace("spotify:user:", "users/").replace(":playlist:", "/playlists/")
        songs_api_endpoint = "{}/{}/tracks".format(SPOTIFY_API_URL, playlistURI)
    else:
        limit = 50
        songs_api_endpoint = "{}/me/tracks".format(SPOTIFY_API_URL)
    
    songs = load_songs(songs_api_endpoint, limit)

    df = pd.DataFrame(songs).drop(columns=['analysis_url', 'id', 'track_href', 'type', 'uri'])
    #, 'key', 'mode', 'time_signature'
    print(df)
    df.to_pickle("./data/" + name + ".pkl")

def data_learn(name = "song_data"):
    df = pd.read_pickle("./data/" + name + ".pkl")
    print("Splitting data")
    X_train, X_test, y_train, y_test = train_test_split(df.drop('name',axis=1), df['name'], test_size=0.30)
    clf = IsolationForest(contamination=0.1)
    print("Fitting data")
    clf.fit(X_train, y_train)

    predictions = clf.predict(X_test)

    unmatch = [name for name, predict in zip(y_test, predictions) if predict < 0]
    print("Mismatched songs: \n", df.loc[df['name'].isin(unmatch)])
    
    count = len(unmatch)

    print("{}/{} misclassified: {:3f}%".format(count, len(y_test), (count/len(y_test)*100)))
    print(df.loc[df['name'].isin(unmatch)].describe())
    
    with open('clf.pkl', 'wb') as fid:
        print("Saved model")
        pickle.dump(clf, fid, 2) 

def predict():
    playlist_url = input("Enter playlist spotify uri:").replace("spotify:user:", "users/").replace(":playlist:", "/playlists/")

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

    print("{}/{} misclassified: {:3f}%".format(count, len(y), (count/len(y)*100)))
    print("Matched: \n", df.loc[df['name'].isin(match)].describe())
    print("Unmatched: \n", df.loc[df['name'].isin(unmatch)].describe())

def main():
    if sys.argv[1] == 'predict':
        predict()
    elif sys.argv[1] == 'learn':
        if len(sys.argv) == 3:
            data_learn(sys.argv[2])
        else:
            data_learn()
    elif sys.argv[1] == 'load':
        if len(sys.argv) == 4:
            data_grab(sys.argv[2], sys.argv[3])
        elif len(sys.argv) == 3:
            data_grab(sys.argv[2])  
        else:
            data_grab()
    else: 
        exit()

if __name__ == "__main__":
    main()  
