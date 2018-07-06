from flask import Flask
app = Flask(__name__)

import spotify_analysis.api
import spotify_analysis.views
