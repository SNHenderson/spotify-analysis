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
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import IsolationForest
import numpy as np
import json

# Authentication Steps, paramaters, and responses are defined at https://developer.spotify.com/web-api/authorization-guide/
# Visit this url to see all the steps, parameters, and expected response.

from spotify_analysis import app

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
#CLIENT_SIDE_URL = os.getenv('HEROKU_URL')
#REDIRECT_URI = "{}/callback/q".format(CLIENT_SIDE_URL)
CLIENT_SIDE_URL = "http://127.0.0.1"
PORT = 5000
REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)

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
        os.makedirs("./spotify_analysis/auth")
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

    with open('./spotify_analysis/auth/header.pkl', 'wb') as fid:
        pickle.dump(AUTH_HEADER, fid, 2) 


    with open('./spotify_analysis/auth/expire.pkl', 'wb') as fid:
        pickle.dump(expire, fid, 2) 

    return render_template("auth.html")

def check_token():
    pkl_file = open('./spotify_analysis/auth/expire.pkl', 'rb')
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

    with open('./spotify_analysis/auth/header.pkl', 'wb') as fid:
        pickle.dump(AUTH_HEADER, fid, 2) 

    with open('./spotify_analysis/auth/expire.pkl', 'wb') as fid:
        pickle.dump(expire, fid, 2) 

@app.route("/data/<filename>")
def data_page(filename):
    #data = data_view(filename + ".pkl").get_json()
    return render_template('output.html', name=filename)

@app.route("/analysis")
def analysis():
    data = [file[:-4] for file in os.listdir("./spotify_analysis/data")]
    return render_template('analyze.html', data=data)
