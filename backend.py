import os, requests, json
import base64
from dotenv import load_dotenv

load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

#look into self looping function to get new auth code every 60 minutes.
def loop_get_Token():
    while(True):
        auth_token=get_auth_Token()
        return auth_token


def get_auth_Token():
    auth_string = client_id + ":" + client_secret
    auth_inbyte = auth_string.encode('utf-8')
    auth_send = base64.b64encode(auth_inbyte).decode('utf-8')
    
    url = "https://accounts.spotify.com/api/token"
    headers = {
        'Authorization' : "Basic " + auth_send,
        'Content-Type' : "application/x-www-form-urlencoded"
    }
    data = {'grant_type':"client_credentials"}

    result = requests.post(url,data=data,headers=headers)
    parsed_result = json.loads(result.text)
    auth_token = parsed_result['access_token']
    print(f"Token valid for: {str(parsed_result['expires_in']/60)} minutes")
    return auth_token

def get_auth_Header(token):
    return {'Authorization': "Bearer " + token}

def search_artist(token, artistName):
    url="https://api.spotify.com/v1/search"
    query = f"?q={artistName}&type=artist&limit=3"

    query_url = url + query
    headers = get_auth_Header(token)
    
    result = requests.get(query_url,headers=headers)
    parsed_result = json.loads(result.text)
    return parsed_result['artists']['items']

#           under exec.
auth_token=get_auth_Token()
artist_obj = search_artist(auth_token,"Weeknd") #getting query from a searchbox at the frontend, routing through asingle cell of the database to prevent
                                                #iteration and delayed get functions, use MERN for simplicity sake.
print(artist_obj[0])