import os
import json
from flask import Flask, request, redirect, g, render_template
import requests
from urllib.parse import quote

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
    response_data = json.loads(post_request.text)
    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]
    token_type = response_data["token_type"]
    expires_in = response_data["expires_in"]

    # Auth Step 6: Use the access token to access Spotify API
    authorization_header = {"Authorization": "Bearer {}".format(access_token)}

    # Get saved songs data
    songs_api_endpoint = "{}/me/tracks".format(SPOTIFY_API_URL)
    params = {
        "limit" : 50,
        "offset" : 0
    }

    display_arr = []
    for _ in range(0,22):
        render_template("index.html", sorted_array=display_arr)
        songs_response = requests.get(songs_api_endpoint, headers=authorization_header, params=params)
        songs_data = json.loads(songs_response.text)
        if songs_data && "items" in songs_data:
            for song in songs_data["items"]:
                song_api_endpoint = "{}/audio-features/{}".format(SPOTIFY_API_URL, song["track"]["id"])
                song_response = requests.get(song_api_endpoint, headers=authorization_header)
                song_data = json.loads(song_response.text)
                display_arr.extend(song_data)
        render_template("index.html", sorted_array=display_arr)
        params["offset"] += 50;    

    # Combine profile and playlist data to display
    return render_template("index.html", sorted_array=display_arr)

if __name__ == "__main__":
    app.run(debug=True)
