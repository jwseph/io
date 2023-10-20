from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from colorthief import ColorThief
import aiohttp

import asyncio
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

@app.get('/get_video_ids')
async def get_video_ids(playlist_id: str):
  return {
    'videoIds': ref.child(playlist_id+'/video_ids').get(),
    'removedVideoIds': ref.child(playlist_id+'/removed_video_ids').get(),
  }

@app.get('/get_playlist_videos')
async def get_playlist_videos(playlist_id: str):
  return ref.child(playlist_id+'/videos').get()

@app.get('/get_channel_info')
async def get_channel_info(channel_url: str):
  return await api.get_channel_info(channel_url)

@app.post('/import')
async def import_(playlist_id: str):
  asyncio.create_task(import_playlist(playlist_id))

async def import_playlist(playlist_id: str):
  if 'stream' in playlist_id: return
  playlist = await api.get_playlist(playlist_id)

  pl_ref = ref.child(playlist_id)
  all_video_ids = set(pl_ref.child('video_ids').get() or {})
  all_video_ids |= set(pl_ref.child('removed_video_ids').get() or {})
  new_removed_ids = all_video_ids - playlist['video_ids'].keys()

  pl_ref.child('videos').update(playlist['videos'])
  pl_ref.child('removed_video_ids').set(dict.fromkeys(new_removed_ids, True))

  del playlist['videos']
  pl_ref.update(playlist)

@app.post('/update')
async def update(playlist_id: str):
  asyncio.create_task(update_playlist(playlist_id))

async def update_playlist(playlist_id: str):
  if 'stream' in playlist_id: return
  pl_ref = ref.child(playlist_id)
  existing_video_ids = set(pl_ref.child('video_ids').get() or {})
  removed_ids = set(pl_ref.child('removed_video_ids').get() or {})

  playlist = await api.get_playlist(playlist_id, existing_video_ids)
  pl_ref.child('videos').update(playlist['videos'])
  pl_ref.child('video_ids').update(playlist['video_ids'])

  new_removed_ids = removed_ids - playlist['video_ids'].keys()
  pl_ref.child('removed_video_ids').set(dict.fromkeys(new_removed_ids, True))

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