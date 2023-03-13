from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='127.0.0.1', port=80)