import socketio
from urllib import parse
from datetime import datetime
from colorsys import hsv_to_rgb
import firebase_admin
from firebase_admin import credentials, auth
import os


cert = {
  "type": "service_account",
  "project_id": "kamiak-chat",
  "private_key_id": "2aab14bfddfcfa4dac51e864a73f98501d35ba43",
  "private_key": os.environ['PRIVATE_KEY'],
  "client_email": "firebase-adminsdk-klupx@kamiak-chat.iam.gserviceaccount.com",
  "client_id": "109175298576378518214",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-klupx%40kamiak-chat.iam.gserviceaccount.com"
}

firebase_app = firebase_admin.initialize_app(credentials.Certificate(cert))
# token = auth.verify_id_token('eyJhbGciOiJSUzI1NiIsImtpZCI6ImE4YmZhNzU2NDk4ZmRjNTZlNmVmODQ4YWY5NTI5ZThiZWZkZDM3NDUiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiSm9zZXBoIEphY2tzb24iLCJwaWN0dXJlIjoiaHR0cHM6Ly9saDMuZ29vZ2xldXNlcmNvbnRlbnQuY29tL2EvQUl0YnZta0k1UEx0V2dRYWFkRHBGZEtscGw2VmVLWXJnUVNWaURNdDZwQ009czk2LWMiLCJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20va2FtaWFrLWNoYXQiLCJhdWQiOiJrYW1pYWstY2hhdCIsImF1dGhfdGltZSI6MTY2MTQ4NjY1NiwidXNlcl9pZCI6InQ1Y3ZCNldoN0ZoZ0ZETWIwOVk4N2lyVjltbTEiLCJzdWIiOiJ0NWN2QjZXaDdGaGdGRE1iMDlZODdpclY5bW0xIiwiaWF0IjoxNjYxNDg2NjU2LCJleHAiOjE2NjE0OTAyNTYsImVtYWlsIjoia29kb21vLm9pc2hpaUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJnb29nbGUuY29tIjpbIjExMzM3MDI3NTUyNDQ0ODE5NDYwMiJdLCJlbWFpbCI6WyJrb2RvbW8ub2lzaGlpQGdtYWlsLmNvbSJdfSwic2lnbl9pbl9wcm92aWRlciI6Imdvb2dsZS5jb20ifX0.hjtHVIorZ6rqxuPw8LK_PpDJxBcM-lujZXmlBUYGhYhZYkhC-JJ5dLamAA0vKVIam5x9m9PiKVDhIYYK6JGhEgqfiR8xmVb55ZEZcnfJFsQAmMJ5MCAibGB8ucveunIVHZEMsOdLq_vqTIrwPF1k19i40PybtbEv2cqztXE_nPXBYNd3fYSZI1Pnxe8TaV4bFseAWpv8mMhCinZ1BP_NB3EQsMnMzw2ukC9wawket8I40OBywRwTMUheW7MS3MZ3y-HnSPn4pKRKLQlbWwtRwDAVibdndJneM_ALPr7A070P6EekMHspmOWjm7o5FoGhDo32-7B1veER2bVHMjSlzg')


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
  return round(datetime.now().timestamp(), 4)


@socket.event
async def connect(sid, environ):
  print(sid, 'connected')
  queries = parse.parse_qs(environ['QUERY_STRING'])
  nickname = queries['nickname'][0].strip().replace('\n', '')
  if not (2 <= len(nickname) <= 24):
    await socket.disconnect(sid)
    return
  users[sid] = {
    'nickname': nickname,
    'color': random_color(nickname+queries['seed'][0])
  }
  await socket.emit('login', {'sid': sid, **users[sid], 'users': users}, to=sid)
  await socket.emit('add user', {'sid': sid, 'user': users[sid]}, skip_sid=sid)

@socket.event
async def disconnect(sid):
  print(sid, 'disconnected')
  await socket.emit('remove user', {'sid': sid}, skip_sid=sid)
  if sid in users: del users[sid]


@socket.on('send message')
async def send_message(sid, data):
  message = data['message'].strip()
  if len(message) == 0: return
  await socket.emit('new message', {'sid': sid, 'message': message}, skip_sid=sid)


@socket.on('start typing')
async def start_typing(sid):
  await socket.emit('start typing', {'sid': sid}, skip_sid=sid)

@socket.on('stop typing')
async def stop_typing(sid):
  await socket.emit('stop typing', {'sid': sid}, skip_sid=sid)


if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=80)
