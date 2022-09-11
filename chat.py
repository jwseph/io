import socketio
from colorsys import hsv_to_rgb
import firebase_admin
from firebase_admin import credentials, auth, db
import time
import os
import re
import uuid
import hashlib
import aiohttp


# region FIREBASE
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
userinfo_ref = ref.child('users')
# endregion FIREBASE


# region PCLOUD SCRAPER
pc_endpoint = 'https://api.pcloud.com'
pc_auth = {'username': os.environ['STORAGE_EMAIL'], 'password': os.environ['STORAGE_PASSWORD']}

async def delete_file(fileid):
  async with aiohttp.ClientSession() as s:
    async with s.get(pc_endpoint+'/deletefile', params={**pc_auth, 'fileid': fileid}) as r:
      pass

async def get_publink(fileid):
  async with aiohttp.ClientSession() as s:
    async with s.get(pc_endpoint+'/getfilepublink', params={**pc_auth, 'fileid': fileid}) as r:
      res = await r.json()
  return res['link']
# endregion PCLOUD SCRAPER


# region SOCKET.IO
origins = [
  'https://kamiak.org',
  'https://beta.kamiak.org',
  'https://kamiak.herokuapp.com',
  'https://kamiakhs.github.io',
  'http://localhost',
  'http://localhost:8000',
  'http://192.168.1.9',
  'http://10.1.10.249',
]
files = {
  '/': 'public/'
}
socket = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=origins, max_http_buffer_size=100*1024*1024+1000)
app = socketio.ASGIApp(socket, static_files=files, socketio_path='/chat/socket.io')
# endregion SOCKET.IO


users = {}
uid_count = {}  # uid: count
salt = uuid.uuid4().hex


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

def jslen(string):
  return int(len(string.encode(encoding='utf_16_le'))/2)

def verify_nickname(nickname):
  return 2 <= jslen(nickname) <= 24

def format_nickname(nickname):
  return re.sub(r'\s+', ' ', nickname.strip())

def generate_nickname(token):
  names = token['name'].split(' ')
  return ' '.join(names[:-1]) if token['email'][:-20].isdigit() else names[-1]

def generate_userinfo(userinfo, token):
  uid = token['uid']
  if uid not in userinfo: userinfo[uid] = {}
  userinfo[uid] = {
    'nickname': generate_nickname(token),
    **userinfo[uid],
    'picture': token['picture'],
    'name': token['name'],
    'email': token['email'].replace('@', '\u200b@'),
  }

def generate_fileid():
  return uuid.uuid4().hex

def generate_filekey(fileid):
  return hashlib.sha1((fileid+salt).encode('utf-8')).hexdigest()
  


@socket.event
async def connect(sid, environ, auth_key):
  print(sid, 'connected')
  try:
    token = auth.verify_id_token(auth_key['token'])
    # assert token['email'].endswith('@mukilteo.wednet.edu')
  except:
    await socket.disconnect(sid)
    return

  uid = token['uid']
  userinfo = userinfo_ref.get()
  generate_userinfo(userinfo, token)
  userinfo_ref.child(uid).set(userinfo[uid])

  users[sid] = {
    'sid': sid,
    'uid': token['uid'],
    'color': '', # random_color(nickname+queries['seed'][0]),
  }
  await socket.emit('login', {'sid': sid, 'users': users, 'sync': userinfo}, to=sid)
  await socket.emit('add user', {'sid': sid, 'user': users[sid], 'timestamp': timestamp()}, skip_sid=sid)

  if uid in uid_count:
    uid_count[uid] += 1
  else:
    uid_count[uid] = 1
    await socket.emit('add uid', {'uid': uid, 'info': userinfo[uid]})


@socket.event
async def disconnect(sid):
  print(sid, 'disconnected')
  if sid in users:
    await socket.emit('remove user', {'sid': sid, 'timestamp': timestamp()}, skip_sid=sid)
    uid = users[sid]['uid']
    del users[sid]

    uid_count[uid] -= 1
    if uid_count[uid] == 0:
      del uid_count[uid]
      await socket.emit('remove uid', {'uid': uid})


@socket.on('send message')
async def send_message(sid, data):
  if len(data['files']) > 0: print('RECEIVED', data['files'][0]['name'])
  message = data['message'].strip()
  files = [{**file, 'id': generate_fileid()} for file in data['files']]
  if len(message) == len(files) == 0: return
  await socket.emit('new message', {'sid': sid, 'message': message, 'files': files, 'timestamp': timestamp()}, skip_sid=sid)
  return {'files': [{**file, 'key': generate_filekey(file['id'])} for file in files]}


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
    await socket.emit('set nickname', {'uid': uid, 'nickname': userinfo_ref.get()[uid]}, to=sid)
    return
  userinfo_ref.child(uid).set({'nickname': nickname})
  await socket.emit('set nickname', {'uid': uid, 'nickname': nickname}, skip_sid=sid)
  print('done')


@socket.on('ping')
async def ping(sid):
  return


@socket.on('update file')
async def update_file(sid, data):
  if data['file']['key'] != generate_filekey(data['file']['id']): return
  publink = await get_publink(data['file']['fileid'])
  await socket.emit('update file', {'file': {'id': data['file']['id'], 'name': data['file']['name']}, 'publink': publink})

@socket.on('upload progress')
async def upload_progress(sid, data):
  if data['file']['key'] != generate_filekey(data['file']['id']): return
  await socket.emit('upload progress', {'file': {'id': data['file']['id']}, 'progress': data['progress']})


if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=80, ws='websockets', ws_max_size=100*1024*1024+1000)
