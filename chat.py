import socketio
from urllib import parse
from random import random, seed
from datetime import datetime
from colorsys import hsv_to_rgb


origins = [
  'https://kamiak.org',
  'https://beta.kamiak.org',
  'https://kamiak.herokuapp.com',
  'http://localhost',
]
files = {
  '/': 'public/'
}
socket = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=origins)
app = socketio.ASGIApp(socket, static_files=files, socketio_path='/chat/socket.io')

users = {}


def random_color(seed_):
  seed(seed_)
  rgb = hsv_to_rgb(random(), 1, .8)
  return '#'+''.join('%02x'%round(i*255) for i in rgb)


def timestamp():
  return round(datetime.now().timestamp(), 4)


@socket.event
async def connect(sid, environ):
  print(sid, 'connected')
  queries = parse.parse_qs(environ['QUERY_STRING']);
  users[sid] = {
    'nickname': queries['nickname'][0],
    'color': random_color(queries['nickname'][0]+queries['seed'][0])
  }
  await socket.emit('data', {'sid': sid, **users[sid], 'users': users}, to=sid)
  await socket.emit('join', {'sid': sid, 'user': users[sid]})

@socket.event
async def disconnect(sid):
  print(sid, 'disconnected')
  await socket.emit('leave', {'sid': sid}, skip_sid=sid)
  if sid in users: del users[sid]


@socket.event
async def send(sid, data):
  message = data['message'].strip()
  if len(message) == 0: return
  await socket.emit('receive', {'sid': sid, 'message': message}, skip_sid=sid)


@socket.event
async def typing_start(sid):
  await socket.emit('typing_start', {'sid': sid}, skip_sid=sid)

@socket.event
async def typing_stop(sid):
  await socket.emit('typing_stop', {'sid': sid}, skip_sid=sid)


if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=80)
