from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import time
import os

from waitlist_fb import ref

def archive_data(timestamp: int, *, canceled: bool):
  '''Saves data from a party and removes it from the parties currently waiting'''
  waiting[timestamp]['canceled'] = canceled
  ref.child(f'history/{timestamp}').set(waiting[timestamp])
  del waiting[timestamp]

app = FastAPI()
app.add_middleware(  # Allow CORS
  CORSMiddleware,
  allow_origins=['*'],
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)

PASSWORD = os.getenv('WAITLIST_PASSWORD')  # Admin sign-in password
waiting = {}

@app.post('/waitlist/create')
async def create(name: str, size: int, contact: str):
  '''Client creates a table request'''
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
  '''Admin sets a party's table as ready'''
  assert password == PASSWORD
  waiting[timestamp]['ready'] = True
  print('Notifying', waiting[timestamp]['contact'])  # TODO: Notify customer using contact

@app.post('/waitlist/remove')
async def remove(timestamp: int, password: str):
  '''Admin removes a party from the currently waiting parties, archiving the data'''
  assert password == PASSWORD
  archive_data(timestamp, canceled=False)

@app.get('/waitlist/waiting')
async def get_waiting(password: str):
  '''Get currently waiting parties'''
  assert password == PASSWORD
  return waiting

@app.get('/waitlist/archive')
async def get_archive(password: str):
  '''Gets archived party data'''
  assert password == PASSWORD
  return ref.child('history').get()

@app.get('/waitlist/is_ready')
async def is_ready(timestamp: int):
  '''Returns whether a party's table is ready'''
  return waiting[timestamp]['ready']

@app.post('/waitlist/cancel')
async def cancel(timestamp: int):
  '''Client cancels a table'''
  archive_data(timestamp, canceled=True)

@app.get('/waitlist/num_waiting')
async def get_num_waiting():
  '''Both client and admin check number of parties waiting'''
  return len(waiting)

if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=80)