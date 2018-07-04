import requests
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest
import numpy as np

# Spotify URLS
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com"
API_VERSION = "v1"
SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

def playlist_songs(header, owner, id):
    pkl_file = open('clf.pkl', 'rb')
    clf = pickle.load(pkl_file)
    prediction = clf.predict(new_vector)

def main():
    playlist_url = input("Enter playlist relative url:")
    pkl_file = open('header.pkl', 'rb')
    header = pickle.load(pkl_file)

    songs_api_endpoint = "{}/{}/tracks".format(SPOTIFY_API_URL, playlist_url)
    params = {
        "limit" : 100,
        "offset" : 0
    }
    print(songs_api_endpoint)
    songs = []
    while True:
        songs_response = requests.get(songs_api_endpoint, headers=header, params=params)
        print(songs_response)
        songs_data = songs_response.json()
        if songs_data and "items" in songs_data:
            if len(songs_data["items"]) < 1:
                print("Finished parsing playlist")
                break
            for song in songs_data["items"]:
                song_api_endpoint = "{}/audio-features/{}".format(SPOTIFY_API_URL, song["track"]["id"])
                song_response = requests.get(song_api_endpoint, headers=header)
                if(song_response.status_code == 429):
                    seconds = song_response.headers["Retry-After"]
                    print("Waiting for ", seconds, " seconds")
                    time.sleep(int(seconds))
                else:
                    if(song_response.status_code == 200):
                        song_data = song_response.json()
                        song_data["name"] = song["track"]["name"]
                        songs.append(song_data)
        else:
            print("Error")
            break
        params["offset"] += 100;  
        print("Loaded ", params["offset"], " songs")

    df = pd.DataFrame(songs).drop(columns=['analysis_url', 'id', 'track_href', 'type', 'uri', 'key', 'mode', 'time_signature'])
    print(df)
    df.dropna(inplace=True)
    print(df)
    
    pkl_file = open('clf.pkl', 'rb')
    clf = pickle.load(pkl_file)
    predictions = clf.predict(df.drop('name', axis=1))
    
    print(predictions)
    y = df['name']
    names = list(zip(y, predictions))
    count = 0
    for pair in names:
        if(pair[1] > 0):
            print(pair[0])
            count += 1

    print("{}/{} misclassified: {}%".format(count, len(y), (count/len(y)*100)))

if __name__ == "__main__":
    main()  