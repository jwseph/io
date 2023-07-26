from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from colorthief import ColorThief
import aiohttp

from tempfile import NamedTemporaryFile

from youtube_api import YoutubeAPI
from yuu_player_fb import ref

api = YoutubeAPI()


app = FastAPI()
app.add_middleware(
  CORSMiddleware,
  allow_origins=['*'],
  allow_credentials=True,
  allow_methods=['*'],
  allow_headers=['*'],
)

@app.get('/')
async def home():
  return 'up'

@app.get('/get')
async def get(playlist: str):
  return await api.get_playlist(playlist)

@app.get('/get_playlist_info')
async def get_playlist_info(playlist_id: str):
  return await api.get_playlist_info(playlist_id)

@app.get('/get_playlist_video_ids')
async def get_playlist_video_ids(playlist_id: str):
  return ref.child(playlist_id+'/video_ids').get()

@app.get('/get_playlist_videos')
async def get_playlist_videos(playlist_id: str):
  return ref.child(playlist_id+'/videos').get()

@app.get('/get_channel_info')
async def get_channel_info(channel_url: str):
  return await api.get_channel_info(channel_url)

@app.post('/import')
async def import_(playlist_id: str):
  playlist = await api.get_playlist(playlist_id)
  ref.child(playlist_id).set(playlist)

@app.post('/update')
async def update(playlist_id: str):
  pl_ref = ref.child(playlist_id)
  existing_video_ids = set(pl_ref.get()['video_ids'])
  playlist = await api.get_playlist(playlist_id, existing_video_ids)
  pl_ref.child('videos').update(playlist['videos'])
  pl_ref.child('video_ids').update(playlist['video_ids'])
  del playlist['videos']
  del playlist['video_ids']
  pl_ref.update(playlist)

@app.get('/get_color')
async def get_color(image_url: str):
  async with aiohttp.ClientSession() as s:
    r = await s.get(image_url)
    content = await r.read()
  ext = '.'+image_url.split('.')[-1]  # This assumes the extension is a suffix
  with NamedTemporaryFile('rb+', suffix=ext) as f:
    f.write(content)
    f.seek(0)
    r, g, b = ColorThief(f).get_color(quality=1)
  return f'#{r:02x}{g:02x}{b:02x}'

if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='127.0.0.1', port=80)