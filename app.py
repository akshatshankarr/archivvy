from flask import Flask, redirect, request, jsonify, session
import os, urllib, requests, json
from dotenv import load_dotenv
from datetime import datetime, date
import sqlite3

#estabilishing connection to sqlite db
conn = sqlite3.connect('e:/cline/zvenv/outreach-flask/artistrecords.sqlite', check_same_thread=False)
curr = conn.cursor()

curr.executescript('''
  drop table if exists recently_played_songs;
  drop table if exists recently_played_artists;
  
  CREATE TABLE recently_played_artists(
    artist_id TEXT PRIMARY KEY NOT NULL,
    name TEXT UNIQUE NOT NULL
  );
  CREATE TABLE recently_played_songs(
    track_id TEXT NOT NULL,
    art_id TEXT NOT NULL,
    title TEXT NOT NULL,
    album_cover TEXT NOT NULL,
    FOREIGN KEY(art_id) REFERENCES recently_played_artists(artist_id)
  );
''')

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = 'http://localhost:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize/'
TOKEN_URL = 'https://accounts.spotify.com/api/token/'
API_QUERY_URL = 'https://api.spotify.com/v1/'

app = Flask(__name__)
app.secret_key = os.getenv("CLIENT_SECRET")

#landing page: login, make playlist, add tracks.
@app.route("/")
def home():
  return '''<a href='/login'>Click here to login</a>
    <form action="/init-archive" method="post" style="display: inline;">
      <button type="submit">Click here to make playlist</button>
    </form>
    <form action="/get-archive" method="post" style="display: inline;">
      <input type="text" name="playlist_id" placeholder="Enter playlist ID" required>
      <button type="submit">Add Tracks to Playlist</button>
    </form>
    '''

#login page
@app.route("/login")
def login():
  #set scope according to app needs
  scope = '''
    user-read-private 
    user-read-email 
    user-read-recently-played
    playlist-modify-private
    playlist-modify-public
    '''
  
  params = {
    'client_id': CLIENT_ID,
    'response_type': 'code',
    'scope': scope,
    'redirect_uri': REDIRECT_URI,
    'show_dialog': True
  }

  auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

  return redirect(auth_url)

#callback for the webapp
@app.route("/callback")
def callback():
  if 'error' in request.args:
    return jsonify({"error": request.args['error']})
  
  if 'code' in request.args:
    req_body = {
      'code': request.args['code'],
      'grant_type': 'authorization_code',
      'redirect_uri': REDIRECT_URI,
      'client_id': CLIENT_ID,
      'client_secret': CLIENT_SECRET
    }

    callback_response = requests.post(TOKEN_URL, data=req_body)
    token_info = callback_response.json()
    session['access_token'] = token_info['access_token']
    session['refresh_token'] = token_info['refresh_token']
    session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']
    print(datetime.now().timestamp())
    print(session['expires_at'])
    return redirect('/recently-played-tracks')
  
#get x number of recently played tracks
@app.route('/recently-played-tracks')
def get_recently_played():
  if 'access_token' not in session:
    return redirect('/login')
  
  if datetime.now().timestamp() > session['expires_at']:
    return redirect('/refresh-token')
  
  headers = {
    'Authorization': f"Bearer {session['access_token']}"
  }

  recently_played_response = requests.get(API_QUERY_URL + 'me/player/recently-played?limit=50', headers=headers)          #change limit accordingly
  parsed = json.loads(recently_played_response.text)
  tracker = len(parsed['items'])
  for i in range(12):
    art_name = (parsed['items'][i]['track']['artists'][0]['name'])
    art_id = ((parsed['items'][i]['track']['artists'][0]['id']))
    track_name = (parsed['items'][i]['track']['name'])
    track_id = ((parsed['items'][i]['track']['id']))
    album_cover = (parsed['items'][i]['track']['album']['images'][0]['url'])
    '''print(album_cover)
    print(art_id)
    print(art_name)                                                                                       --debug
    print(track_id)
    print(track_name)'''
    curr.execute('insert or ignore into recently_played_artists (artist_id, name) values (?,?)', (art_id, art_name,))
    curr.execute('insert into recently_played_songs (track_id,art_id,title,album_cover) values (?,?,?,?)', (track_id, art_id, track_name,album_cover,))
    conn.commit()                                                                                         #commit db changes after every iteration
  playlists = recently_played_response.json()
  return jsonify(playlists)

#creating the archiving playlist
@app.route('/init-archive', methods=['POST'])
def make_archive():
  if 'access_token' not in session:
    return redirect('/login')
  
  if datetime.now().timestamp() > session['expires_at']:
    return redirect('/refresh-token')
  
  headers = {
    'Authorization': f"Bearer {session['access_token']}",
    'Content-Type' : 'application/json'
  }

  #getting userid
  user_response = requests.get(f'{API_QUERY_URL}me', headers=headers)
  user_id = user_response.json()['id']

  #getting date for archive name
  playlistName = 'Archive of ' + date.today().strftime('%b-%d-%Y')

  #initializing playlist info
  playlist_data={
    'name': playlistName,
    'description': 'Archived {0}'.format(date.today().strftime('%B %d, %Y')),
    'public': False
  }

  init_archvie_response = requests.post(f'{API_QUERY_URL}users/{user_id}/playlists', headers=headers, data=json.dumps(playlist_data))
  playlist_id = init_archvie_response.json()['id']

  return jsonify({"playlist_id" : playlist_id, 'message': 'Copy this playlist id to paste in the form!'})

#add tracks to the archive
@app.route('/get-archive', methods = ['POST'])
def add_tracks_to_playlist():
  playlist_id = request.form.get('playlist_id')
  if not playlist_id:
    return jsonify({'error': 'Playlist ID is required'}), 400
  
  if 'access_token' not in session:
    return redirect('/login')
  
  if datetime.now().timestamp() > session['expires_at']:
    return redirect('/refresh-token')
  
  headers={
    'Authorization': f"Bearer {session['access_token']}",
    'Content-Type' : 'application/json'
  }
  
  #Replace with a separate copy of a database if multiple sessions to archive.
  #connect = sqlite3.connect('e:/cline/zvenv/outreach-flask/artistrecords_indie.sqlite', check_same_thread=False)
  #curr_indie = connect.cursor()
  curr.execute('SELECT track_id FROM recently_played_songs')
  trackid_cursor = curr.fetchall()
  tracks_uris = [f'spotify:track:{track[0]}' for track in trackid_cursor]

  #iterating instead of at once to get reverse order in the playlist; can reverse uri array and pass all tracks at once.
  for uri in tracks_uris:
    payload = {
      'uris': [uri],
      'position': 0
    }
    print(payload)
    get_archive_response = requests.post(f'{API_QUERY_URL}playlists/{playlist_id}/tracks', headers=headers, data=json.dumps(payload))

    if get_archive_response.status_code != 201:
      return jsonify(get_archive_response.json(), get_archive_response.status_code)

  return jsonify({'message': 'Tracks added successfully!'})

#route to refresh the access token after expiry
@app.route('/refresh-token')
def refresh_token():
  if 'refresh_token' not in session:
    return redirect('/login')

  if datetime.now().timestamp() > session['expires_at']:
    req_body = {
      'grant_type': 'refresh_token',
      'refresh_token': session['refresh_token'],
      'client_id': CLIENT_ID,
      'client_secret': CLIENT_SECRET
    }

    response = requests.post(TOKEN_URL, data=req_body)
    new_token_info= response.json()
    session['access_token'] = new_token_info['access_token']
    session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

  return redirect('/recently-played-tracks')
  
if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True)