from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import time
import os

from waitlist_fb import ref

app = FastAPI()
app.add_middleware(
  CORSMiddleware,
  allow_origins=['*'],
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)

PASSWORD = os.getenv('WAITLIST_PASSWORD')
waiting = {}

@app.post('/waitlist/create')
async def create(name: str, size: int, contact: str):
  assert name.strip() and size > 0 and contact.strip()
  print('create')
  timestamp = time.time_ns()
  waiting[timestamp] = {
    'name': name.strip(),
    'size': size,
    'contact': contact.strip(),
    'ready': False,
  }
  return timestamp

@app.post('/waitlist/ready')
async def ready(timestamp: int, password: str):
  assert password == PASSWORD
  waiting[timestamp]['ready'] = True
  # Notify customer
  print('Notifying', waiting[timestamp]['contact'])

@app.post('/waitlist/remove')
async def remove(timestamp: int, password: str):
  assert password == PASSWORD
  ref.child(f'history/{timestamp}').set(waiting[timestamp])
  del waiting[timestamp]

@app.get('/waitlist/waiting')
async def get_waiting(password: str):
  assert password == PASSWORD
  return waiting

@app.get('/waitlist/is_ready')
async def is_ready(timestamp: int):
  return waiting[timestamp]['ready']

@app.post('/waitlist/cancel')
async def cancel(timestamp: int):
  del waiting[timestamp]

@app.get('/waitlist/num_waiting')
async def get_num_waiting():
  return len(waiting)

if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=80)