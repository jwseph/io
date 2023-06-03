from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import random

from giftbox_fb import ref

def generate_id() -> str:
  return uuid.uuid4().hex

app = FastAPI()
app.add_middleware(
  CORSMiddleware,
  allow_origins=['*'],
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)

PASSWORD = os.getenv('GIFTBOX_PASSWORD')

@app.get('/')
async def home():
  return 'up'

@app.get('/get_events')
async def get_events(password: str) -> dict[dict]:
  assert password == PASSWORD
  events = ref.child('events').get() or {}
  for event in events.values():
    if 'gifts' not in event:
      event['gifts'] = {}
  return events

@app.post('/add_event')
async def add_event(password: str, event_name: str, event_start_ms: int, event_end_ms: int):
  assert password == PASSWORD
  event_id = generate_id()
  ref.child(f'events/{event_id}').set({
    'name': event_name,
    'start_ms': event_start_ms,
    'end_ms': event_end_ms,
  })

@app.post('/add_gift')
async def add_gift(password: str, event_id: str, gift_name: str, gift_quantity: int, gift_points: int):
  assert password == PASSWORD
  gift_id = generate_id()
  ref.child(f'events/{event_id}/gifts/{gift_id}').set({
    'name': gift_name,
    'quantity': gift_quantity,
    'points': gift_points,
  })

@app.post('/update_gift')
async def update_gift(password: str, event_id: str, gift_id: str, gift_name: str = None, gift_quantity: int = None, gift_points: int = None):
  assert password == PASSWORD
  gift = {}
  if gift_name is not None: gift['name'] = gift_name
  if gift_quantity is not None: gift['quantity'] = gift_quantity
  if gift_points is not None: gift['points'] = gift_points
  ref.child(f'events/{event_id}/gifts/{gift_id}').update(gift)

@app.get('/pick_gift')
async def pick_gift(password: str, event_id: str) -> str:
  assert password == PASSWORD
  gifts = ref.child(f'events/{event_id}/gifts').get()
  n = sum(gift['points'] for gift in gifts.values() if gift['quantity'])
  i = int(random.random()*n)
  for gift_id, gift in gifts.values():
    if not gift['quantity']: continue
    i -= gift['points']
    if i > 0:
      choice = gift_id
  gifts[choice]['quantity'] -= 1
  return choice

if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=80)