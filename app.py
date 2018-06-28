import os, time, base64
from threading import Thread
from io import BytesIO
from flask import Flask, request, redirect, g, render_template
import requests
from urllib.parse import quote
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt

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
#CLIENT_SIDE_URL = "http://127.0.0.1"
#PORT = 8080
#REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)

SCOPE = "user-library-read"
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
    # Auth Step 1: Authorization
    url_args = "&".join(["{}={}".format(key, quote(val)) for key, val in auth_query_parameters.items()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
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

    # Auth Step 6: Use the access token to access Spotify API
    AUTH_HEADER = {"Authorization": "Bearer {}".format(access_token)}

    thread = Thread(target=data_grab, kwargs={'header': AUTH_HEADER})
    thread.start()
    return render_template("loading.html")

@app.route("/data")
def data_view():
    try:
        df = pd.read_pickle("./song_data.pkl")
    except Exception as e:
        print(e)
        return render_template("loading.html")
    figures = []
    for col in df.columns:
        if(col != 'name'):
            print(df[col])
            fig = df[col].astype(float).sort_values().plot(kind = 'box', legend=True).get_figure()
            png_output = BytesIO()
            fig.savefig(png_output, format='png')
            png_output.seek(0)
            figdata_png = base64.b64encode(png_output.getvalue()).decode('ascii')
            figures.append(figdata_png)
            plt.clf()

            fig = df[col].astype(float).sort_values().plot(kind = 'hist', legend=True).get_figure()
            png_output = BytesIO()
            fig.savefig(png_output, format='png')
            png_output.seek(0)
            figdata_png = base64.b64encode(png_output.getvalue()).decode('ascii')
            figures.append(figdata_png)
            plt.clf()
    return render_template('output.html', data=df, figures=figures) 

def data_grab(header):
    # Get saved songs data
    songs_api_endpoint = "{}/me/tracks".format(SPOTIFY_API_URL)
    params = {
        "limit" : 50,
        "offset" : 0
    }
    
    songs = []
    max = 22
    for _ in range(0, max):
        songs_response = requests.get(songs_api_endpoint, headers=header, params=params)
        songs_data = songs_response.json()
        #print(songs_data)
        if songs_data and "items" in songs_data:
            for song in songs_data["items"]:
                song_api_endpoint = "{}/audio-features/{}".format(SPOTIFY_API_URL, song["track"]["id"])
                #print("Sending request to ", song_api_endpoint)
                song_response = requests.get(song_api_endpoint, headers=header)
                if(song_response.status_code == 429):
                    seconds = song_response.headers["Retry-After"]
                    print("Waiting for ", seconds, " seconds")
                    time.sleep(int(seconds))
                else:
                    song_data = song_response.json()
                    #print("Received song ", song_data)
                    song_data["name"] = song["track"]["name"]
                    songs.append(song_data)
        params["offset"] += 50;  
        print("Loaded ", params["offset"], "/", max*50, " songs")

    df = pd.DataFrame(songs).drop(columns=['analysis_url', 'id', 'track_href', 'type', 'uri', 'key', 'mode', 'time_signature']).dropna(axis=1, how='all')
    df.to_pickle("./song_data.pkl")

if __name__ == "__main__":
    app.run(debug=True, port=PORT)
