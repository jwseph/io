from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import random
import time

from giftbox_fb import ref

def generate_id() -> str:
  return uuid.uuid4().hex

def get_all_events() -> list:
  events = ref.child('events').get() or {}
  for event in events.values():
    event['gifts'] = event.get('gifts', {})
    event['claims'] = event.get('claims', {})
  return events

def get_event_id() -> str:
  now = time.time_ns()//10**6  # UTC, might not correspond to PST times
  for event_id, event in get_all_events().items():
    if event['start_ms'] <= now < event['end_ms']:
      return event_id
  raise RuntimeError('No event is active right now')

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
  return 'giftbox'

@app.get('/get_events')
async def get_events(password: str):
  assert password == PASSWORD
  return get_all_events()

@app.get('/get_event')
async def get_event(password: str):
  assert password == PASSWORD
  event = ref.child(f'events/{get_event_id()}').get()
  event['gifts'] = event.get('gifts', {})
  event['claims'] = event.get('claims', {})
  return event

@app.post('/add_event')
async def add_event(password: str, event_name: str, event_start_ms: int,
                    event_end_ms: int):
  assert password == PASSWORD
  event_name = event_name.strip()
  assert event_name and event_start_ms < event_end_ms
  # Ensure event does not overlap
  for event in get_all_events().values():
    assert event['end_ms'] < event_start_ms or event_end_ms < event['start_ms']
  event_id = generate_id()
  ref.child(f'events/{event_id}').set({
    'name': event_name,
    'start_ms': event_start_ms,
    'end_ms': event_end_ms,
  })

@app.post('/delete_event')
async def delete_event(password: str, event_id: str):
  assert password == PASSWORD
  ref.child(f'events/{event_id}').delete()

@app.post('/add_gift')
async def add_gift(password: str, gift_name: str, gift_quantity: int,
                   gift_points: int, gift_image: str):
  assert password == PASSWORD
  gift_name = gift_name.strip()
  gift_image = gift_image.strip()
  assert gift_name and gift_points and gift_image and gift_quantity
  gift_id = generate_id()
  ref.child(f'events/{get_event_id()}/gifts/{gift_id}').set({
    'name': gift_name,
    'quantity': gift_quantity,
    'points': gift_points,
    'image': gift_image,
  })

@app.post('/delete_gift')
async def delete_gift(password: str, event_id: str, gift_id: str):
  assert password == PASSWORD
  ref.child(f'events/{event_id}/gifts/{gift_id}').delete()

@app.get('/pick_gift')
async def pick_gift(password: str):
  assert password == PASSWORD
  gifts_ref = ref.child(f'events/{get_event_id()}/gifts')
  gifts = gifts_ref.get()
  n = sum(gift['points'] for gift in gifts.values() if gift['quantity'])
  i = int(random.random()*n)
  for gift_id, gift in gifts.items():
    if not gift['quantity']: continue
    if i >= 0: choice = gift_id
    i -= gift['points']
  gift = gifts_ref.child(choice).get()
  gift['id'] = choice
  return gift

@app.post('/claim_gift')
async def claim_gift(password: str, gift_id: str,
                     first_name: str, last_name: str, phone: str, email: str,
                     address: str, city: str, state: str, zip_code: str):
  assert password == PASSWORD
  first_name, last_name, = first_name.strip(), last_name.strip()
  phone, email = phone.strip(), email.strip()
  address, city = address.strip(), city.strip()
  state, zip_code = state.strip(), zip_code.strip()
  assert first_name and last_name and phone and email and address
  assert city and state and zip_code.isnumeric() and len(zip_code) == 5
  event_ref = ref.child(f'events/{get_event_id()}')
  event_ref.child(f'gifts/{gift_id}/quantity').transaction(
    lambda x: x-1 if x else None  # raises TransactionAbortedError when x == 0
  )
  event_ref.child(f'claims/{generate_id()}').set({
    'gift_id': gift_id,
    'claimed': False,
    'first_name': first_name,
    'last_name': last_name,
    'phone': phone,
    'email': email,
    'address': address,
    'city': city,
    'state': state,
    'zip_code': zip_code,
  })

if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=80)