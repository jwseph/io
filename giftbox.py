from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from giftbox_fb import ref

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

if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=80)