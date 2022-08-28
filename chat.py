import socketio
from urllib import parse
from colorsys import hsv_to_rgb
import firebase_admin
from firebase_admin import credentials, auth, db
import time
import os
import re


cert = {
  "type": "service_account",
  "project_id": "kamiak-chat",
  "private_key_id": os.environ['PRIVATE_KEY_ID'],
  "private_key": os.environ['PRIVATE_KEY'],
  "client_email": "firebase-adminsdk-klupx@kamiak-chat.iam.gserviceaccount.com",
  "client_id": "109175298576378518214",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-klupx%40kamiak-chat.iam.gserviceaccount.com"
}

firebase_admin.initialize_app(credentials.Certificate(cert), {'databaseURL': 'https://kamiak-chat-default-rtdb.firebaseio.com/'})

ref = db.reference('/')
users_ref = ref.child('users')


origins = [
  'https://kamiak.org',
  'https://beta.kamiak.org',
  'https://kamiak.herokuapp.com',
  'https://kamiakhs.github.io',
  'http://localhost',
  'http://localhost:8000',
  'http://192.168.1.9',
  'http://10.1.10.249'
]
files = {
  '/': 'public/'
}
socket = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=origins)
app = socketio.ASGIApp(socket, static_files=files, socketio_path='/chat/socket.io')

users = {}


def random_hue(seed):
  hash = 7
  for c in seed:
    hash = (ord(c)+(hash<<5)-(hash>>2))%47160
  return hash%360

def random_color(seed):
  rgb = hsv_to_rgb(random_hue(seed)/360, 1, .8)
  return '#'+''.join('%02x'%round(i*255) for i in rgb)

def timestamp():
  return time.time_ns()//1000000

def verify_nickname(nickname):
  return 2 <= len(nickname) <= 24

def format_nickname(nickname):
  return re.sub(r'\s+', ' ', nickname.strip())

def generate_nickname(token):
  names = token['name'].split(' ')
  return ' '.join(names[:-1]) if token['email'][:-20].isdigit() else names[-1]
  


@socket.event
async def connect(sid, environ, auth_key):
  print(sid, 'connected')
  queries = parse.parse_qs(environ['QUERY_STRING'])
  try:
    token = auth.verify_id_token(auth_key['token'])
    # assert token['email'].endswith('@mukilteo.wednet.edu')
  except:
    await socket.disconnect(sid)
    return
  
  users_ref_save = users_ref.get()
  if token['uid'] in users_ref_save:
    nickname = users_ref_save[token['uid']]['nickname']
  else:
    nickname = generate_nickname(token)
    users_ref.child(token['uid']).set({'nickname': nickname})
    users_ref_save[token['uid']] = {'nickname': nickname}

  users[sid] = {
    'sid': sid,
    'name': token['name'],
    'picture': token['picture'],
    'email': token['email'].replace('@', '\u200b@'),
    'uid': token['uid'],
    'color': random_color(nickname+queries['seed'][0]),
  }
  await socket.emit('login', {'sid': sid, 'users': users, 'sync': users_ref_save}, to=sid)
  await socket.emit('add user', {'sid': sid, 'user': users[sid], 'sync': users_ref_save, 'timestamp': timestamp()}, skip_sid=sid)

@socket.event
async def disconnect(sid):
  print(sid, 'disconnected')
  await socket.emit('remove user', {'sid': sid, 'timestamp': timestamp()}, skip_sid=sid)
  if sid in users: del users[sid]


@socket.on('send message')
async def send_message(sid, data):
  message = data['message'].strip()
  if len(message) == 0: return
  await socket.emit('new message', {'sid': sid, 'message': message, 'timestamp': timestamp()}, skip_sid=sid)


@socket.on('start typing')
async def start_typing(sid):
  await socket.emit('start typing', {'sid': sid}, skip_sid=sid)

@socket.on('stop typing')
async def stop_typing(sid):
  await socket.emit('stop typing', {'sid': sid}, skip_sid=sid)


@socket.on('set nickname')
async def set_nickname(sid, data):
  nickname = format_nickname(data['nickname'])
  print('set nickname '+nickname)
  uid = users[sid]['uid']
  if not verify_nickname(nickname):
    await socket.emit('set nickname', {'uid': uid, 'nickname': users_ref.get()[uid]}, to=sid)
    return
  users_ref.child(uid).set({'nickname': nickname})
  await socket.emit('set nickname', {'uid': uid, 'nickname': nickname}, skip_sid=sid)
  print('done')


@socket.on('ping')
async def ping(sid):
  return


if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=80)
