import os, time, errno
from flask import Flask, request, redirect, render_template, jsonify, g, make_response
import requests
from urllib.parse import quote
import pandas as pd
import pickle
import json

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

# Set directory name if running on flask or gunicorn
dirname = os.getcwd().split('\\')[-1]
url_prefix = "spotify_analysis/" if os.path.isdir("spotify_analysis") else ""

# Server-side Parameters
CLIENT_SIDE_URL = os.getenv('URL')
REDIRECT_URI = "{}/callback/q".format(CLIENT_SIDE_URL)
# CLIENT_SIDE_URL = "http://127.0.0.1"
# PORT = 8000
# REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)

# Authorization Query Parameters
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

def after_this_request(f):
    if not hasattr(g, 'after_request_callbacks'):
        g.after_request_callbacks = []
    g.after_request_callbacks.append(f)
    return f

@app.after_request
def call_after_request_callbacks(response):
    for callback in getattr(g, 'after_request_callbacks', ()):
        callback(response)
    return response

@app.route("/")
def index():
    """Sets the auth url then redirects"""
    url_args = "&".join(["{}={}".format(key, quote(val)) for key, val in auth_query_parameters.items()])
    auth_url = "{}/?{}".format(SPOTIFY_AUTH_URL, url_args)
    print(auth_url)
    return redirect(auth_url)

@app.route("/callback/q")
def callback():
    """Receives code, requests token and stores data"""

    auth_token = request.args['code']
    code_payload = {
        "grant_type": "authorization_code",
        "code": str(auth_token),
        "redirect_uri": REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }
    post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload)

    response_data = post_request.json()
    if not 'access_token' in response_data:
        return redirect("/")
    access_token = response_data["access_token"]
    refresh_token = response_data["refresh_token"]
    token_type = response_data["token_type"]
    g.expires_in = response_data["expires_in"]

    g.AUTH_HEADER = {"Authorization": "Bearer {}".format(access_token)}

    resp = make_response(render_template("auth.html"))
    resp.set_cookie('token', value = access_token, max_age=g.expires_in, httponly=True)
    resp.set_cookie('refresh', refresh_token, httponly=True)
    return resp

@app.before_request
def check_token():
    
    """Checks and renews token if applicable"""
    access_token = request.cookies.get('token')

    if access_token is None:
        refresh_token = request.cookies.get('refresh')

        code_payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
        }

        post_request = requests.post(SPOTIFY_TOKEN_URL, data=code_payload)
        response_data = post_request.json()
        
        if "access_token" not in response_data:
            return
        access_token = response_data["access_token"]

        if('refresh_token' in response_data):
            refresh_token = response_data["refresh_token"]
        
        if('expires_in' in response_data):
            g.expires_in = response_data["expires_in"]

        @after_this_request
        def set_token(resp):
            resp.set_cookie('token', access_token, max_age=g.expires_in, httponly=True)
            resp.set_cookie('refresh', refresh_token, httponly=True)

@app.route("/data/<filename>")
def data_page(filename):
    """Returns the data page
    
    Arguments:
    filename -- the name of the file to view
    """
    return render_template('output.html', name=filename)

@app.route("/analysis")
def analysis():
    """Returns the page for interacting with the API"""
    data = [file[:-4] for file in os.listdir('./' + url_prefix + 'data')]
    return render_template('analyze.html', data=data)
