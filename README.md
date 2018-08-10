# spotify-analysis
Analyzing spotify data with computers. This project is an attempt to use outlier detection to classify music, based off of [Spotify's public API.](https://developer.spotify.com/documentation/web-api/) This is done with SKLearn's OneClassSVM. 

## Using hosted version:

### Warning: your data may be deleted at any time

Navigate to https://spotify-data.herokuapp.com/

Login to Spotify and give the client permissions. You will receive a token. 

On the analysis page, you can load and save more data sets from Spotify, train a model off existing data sets, or predict from a data set based on the model 

## Running locally:

### Create spotify client

Create a Client on the [spotify developers site.](https://developer.spotify.com/dashboard/applications)

### Cloning project

`git clone https://github.com/SNHenderson/spotify-analysis.git`

### Export environment variables:

#### Linux/Mac/Bash:

`export CLIENT_ID = your client id`

`export CLIENT_SECRET = your client secret id`

`export URL = your localhost url, should probably be "http://127.0.0.1:8000"`

#### Windows:

`set CLIENT_ID = your client id`

`set CLIENT_SECRET = your client secret id`

`set URL = your localhost url, should probably be "http://127.0.0.1:8000"`

### Install dependencies 

This project has setuptools, but it is not necessary to use for running. Navigate to spotify_analysis and run:

`pip install -r requirements.txt`

### Run app

#### Linux/Mac/Bash:

`gunicorn spotify_analysis:app -t 300 --log-file=-`

#### Windows:

(Untested)

`export FLASK_APP=spotify_analysis`

`pip install -e .`

`flask run`

## Dependencies:

**Requests:** Used for GET requests to Spotify API

**Flask:** Used for mapping routes for UI and API

**Gunicorn:** WSGI HTTP Server for running on Unix

**Pandas:** Used to store the data

**Matplotlib:** Creates plots of data (*/data/:dataname*)

**SKLearn:** OneClassSVM Algorithm, used for classifying songs
