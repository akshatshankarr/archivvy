from flask import Flask, render_template, redirect, request, jsonify, session
import urllib, requests, json
from datetime import datetime, date
import sqlite3

from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, AUTH_URL, TOKEN_URL, API_QUERY_URL, DB_PATH
from db_helper import init_db

app = Flask(__name__)
app.secret_key = CLIENT_SECRET

@app.route("/home")
def home():
  if 'access_token' not in session:
    return redirect('/')
  return render_template('home.html')

@app.route("/about")
def about():
  return render_template('about.html')

@app.route("/")
def landing():
  if 'access_token' in session:
    return redirect('/home')
  return render_template('landing.html')

@app.route("/privacy")
def privacy():
  return render_template('privacy.html')

@app.route("/logout")
def logout():
  session.clear()
  return redirect("/")


@app.route("/login")
def login():
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

    return redirect('/home')

@app.route('/get-tracks')
def get_tracks():
  if 'access_token' not in session:
    return redirect('/login')
  
  if datetime.now().timestamp() > session['expires_at']:
    return redirect('/refresh-token')
  
  headers = {
    'Authorization': f"Bearer {session['access_token']}"
  }

  response = requests.get(API_QUERY_URL + 'me/player/recently-played?limit=50', headers=headers)          #change limit accordingly or pass a count
  if response:
    print("success")
  else:
    print("gg")
  body = json.loads(response.text)
  
  init_db(DB_PATH)
  with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
    curr = conn.cursor()
    for item in body['items']:
      artist = item['track']['artists'][0]
      curr.execute('insert or ignore into recently_played_artists (artist_id, name) values (?,?)', (artist['id'], artist['name'],))
      track = item['track']
      album_cover = track['album']['images'][0]['url']
      curr.execute('insert into recently_played_songs (track_id,art_id,title,album_cover) values (?,?,?,?)', (track['id'], artist['id'], track['name'],album_cover,))
      conn.commit()
    curr.execute('SELECT DISTINCT title, album_cover, track_id FROM recently_played_songs')
    tracks = curr.fetchall()
    print(tracks)

  return render_template('tracks_added.html', tracks=tracks)

@app.route('/get-archive', methods = ['GET', 'POST'])
def create_archive():
  if 'access_token' not in session:
    return redirect('/login')
  if datetime.now().timestamp() > session['expires_at']:
    return redirect('/refresh-token')
  if request.method == 'GET':
    return render_template('create_archive.html')
  else:
    #get user id
    headers = {
      'Authorization': f"Bearer {session['access_token']}",
      'Content-Type': 'application/json'
    }
    user_response = requests.get(f'{API_QUERY_URL}me', headers=headers)
    user_id = user_response.json()['id']

    #create playlist
    playlist_name = 'Archive of ' + date.today().strftime('%b-%d-%Y')
    playlist_data = {
      'name' : playlist_name,
      'description' : f'Archived {date.today().strftime("%B, %d, %y")}',
      'public' : False
    }

    response = requests.post(f'{API_QUERY_URL}users/{user_id}/playlists', headers=headers, data=json.dumps(playlist_data))
    
    if response.status_code != 201:
      return jsonify(response.json(), response.status_code)
    playlist_id = response.json()['id']

    #add tracks to playlist
    with sqlite3.connect(DB_PATH) as conn:
        curr = conn.cursor()
        curr.execute('SELECT track_id FROM recently_played_songs')
        track_uris = [f'spotify:track:{track[0]}' for track in reversed(curr.fetchall())]
      
    payload = {
      'uris': track_uris
    }

    response = requests.post(f'{API_QUERY_URL}playlists/{playlist_id}/tracks', headers=headers, data=json.dumps(payload))

    if response.status_code != 201:
      return jsonify(response.json(), response.status_code)
    
    return render_template('get_archive.html', playlist_id = playlist_id)

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

  return redirect('/home')

@app.route('/remove-track', methods=['POST'])
def remove_track():
    track_id = request.json.get('track_id')
    if not track_id:
        return jsonify({'success': False, 'error': 'No track_id provided'}), 400
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        curr = conn.cursor()
        curr.execute('DELETE FROM recently_played_songs WHERE track_id = ?', (track_id,))
        conn.commit()
    return jsonify({'success': True})

#debug
@app.route('/routes')
def show_routes():
    return '<br>'.join([str(rule) for rule in app.url_map.iter_rules()])
  
if __name__ == "__main__":
  app.run(host='0.0.0.0', debug=True)