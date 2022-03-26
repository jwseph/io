import socketio
from urllib import parse
# from random import random, seed
from datetime import datetime
from colorsys import hsv_to_rgb


origins = [
  'https://kamiak.org',
  'https://beta.kamiak.org',
  'https://kamiak.herokuapp.com',
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
    socket.disconnect(sid)
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
  uvicorn.run(app, host='0.0.0.0', port=8000)
