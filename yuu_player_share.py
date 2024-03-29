import socketio
import aiohttp

import time
import random
import asyncio

from youtube_api import YoutubeAPI
from yuu_player_fb import ref

class Stream:
    @staticmethod
    def generate_id():
        stream_id = None
        while stream_id is None or stream_id in stream_ids:
            stream_id = f'{random.randint(0, 0xffffff):06x}'
        return stream_id

    def __init__(self, stream_id: str):
        self.stream_id: str = stream_id
        stream_ref = ref.child('streams/'+self.stream_id)
        self.videos: dict[str, dict] = stream_ref.child('videos').get() or {}
        self.queue: list[str] = stream_ref.child('queue').get() or []
        self.index: int = stream_ref.child('index').get() or 0
        self.progress: float = 0
        self.last_updated: float = time.time()
        self.playing = True
        self.listeners: list[str] = []
        self.loop_one = False
        self.save()

    def save(self):
        backup = {
            'videos': self.videos,
            'queue': self.queue,
            'index': self.index,
        }
        if hasattr(self, 'last_backup') and backup == self.last_backup:
            return

        ref.child('streams/'+self.stream_id).set(backup)
        self.last_backup = backup

    async def add_listener(self, sid: str):
        self.update_progress()
        if sid in self.listeners: return
        self.listeners.append(sid)
        await self.notify_listeners()

    async def remove_listener(self, sid: str):
        self.update_progress()
        self.listeners.remove(sid)
        await self.notify_listeners()

    def get_duration(self) -> float:
        return self.videos[self.queue[self.index]]['duration']

    def get_video_id(self) -> str | None:
        return self.queue[self.index] if self.queue else None

    def update_progress(self):
        dt = time.time() - self.last_updated
        self.last_updated += dt
        if not self.queue or not self.playing: return
        self.progress += dt
        while self.progress > self.get_duration():
            self.progress -= self.get_duration()
            if not self.loop_one:
                self.index = (self.index+1)%len(self.queue)

    async def set_progress(self, progress):
        self.update_progress()
        assert 0 <= progress < self.get_duration()+1
        self.progress = progress
        await self.notify_listeners()

    async def add_video(self, video_id: str):
        self.update_progress()
        async with aiohttp.ClientSession() as s:
            videos = await api.get_video_info(s, [video_id])
        self.queue.extend(videos.keys()-self.videos.keys())
        self.videos |= videos
        await self.notify_listeners()

    async def add_playlist(self, playlist_id: str):
        self.update_progress()
        playlist = await api.get_playlist(playlist_id)
        videos = playlist['videos']
        self.queue.extend(videos.keys()-self.videos.keys())
        self.videos |= videos
        await self.notify_listeners()

    async def remove_video(self, video_id: str):
        self.update_progress()
        i = self.queue.index(video_id)
        if i < self.index: self.index -= 1
        del self.queue[i]
        del self.videos[video_id]
        self.index %= len(self.queue) or 1
        await self.notify_listeners()

    async def select_video(self, video_id: str):
        self.update_progress()
        self.index = self.queue.index(video_id)
        self.progress = 0
        await self.notify_listeners()

    async def toggle_playing(self):
        self.update_progress()
        self.playing = not self.playing
        await self.notify_listeners()

    async def toggle_loop_one(self):
        self.update_progress()
        self.loop_one = not self.loop_one
        await self.notify_listeners()

    async def shuffle(self):
        self.update_progress()
        random.shuffle(self.queue)
        self.index = self.progress = 0
        await self.notify_listeners()

    def __iter__(self):
        yield from {
            'queue': self.queue,
            'index': self.index,
            'progress': self.progress,
            'videos': self.videos,
            'playing': self.playing,
            'listeners': len(self.listeners),
            'loop_one': self.loop_one,
        }.items()

    async def notify_listeners(self):
        await sio.emit('update', dict(self))
        self.save()

async def remove_listener(sid: str):
    if sid not in stream_ids: return
    stream_id = stream_ids[sid]
    del stream_ids[sid]
    stream = streams[stream_id]
    await stream.remove_listener(sid)
    # if not stream.listeners:
    #     del streams[stream_id]

api = YoutubeAPI()

origins = [
    'https://yuu.pages.dev',
    'http://yuu.pages.dev',
    'http://localhost',
]

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = socketio.ASGIApp(sio, socketio_path='/yuu_share/socket.io')

streams: dict[str, Stream] = {}
stream_ids: dict[str, str] = {}

@sio.event
async def connect(sid: str, environ: dict):
    print(f'[Yuu] {sid} connected')

@sio.event
async def disconnect(sid: str):
    print(f'[Yuu] {sid} disconnected')
    await remove_listener(sid)

@sio.event
async def create_stream(sid: str) -> str:
    stream_id = Stream.generate_id()
    streams[stream_id] = Stream(stream_id)
    return stream_id

@sio.event
async def leave_stream(sid: str):
    await remove_listener(sid)

@sio.event
async def get_stream(sid: str, data: dict) -> dict:
    stream_id = data['stream_id']
    if stream_id not in streams:
        streams[stream_id] = Stream(stream_id)
    stream = streams[stream_id]
    await stream.add_listener(sid)
    stream_ids[sid] = stream_id
    return dict(stream)

@sio.event
async def add_video(sid: str, data: dict):
    await streams[data['stream_id']].add_video(data['video_id'])

@sio.event
async def add_playlist(sid: str, data: dict):
    asyncio.create_task(add_playlist_(data))

async def add_playlist_(data: dict):
    await streams[data['stream_id']].add_playlist(data['playlist_id'])

@sio.event
async def remove_video(sid: str, data: dict):
    await streams[data['stream_id']].remove_video(data['video_id'])

@sio.event
async def select_video(sid: str, data: dict):
    await streams[data['stream_id']].select_video(data['video_id'])

@sio.event
async def toggle_playing(sid: str, data: dict):
    await streams[data['stream_id']].toggle_playing()

@sio.event
async def toggle_loop_one(sid: str, data: dict):
    await streams[data['stream_id']].toggle_loop_one()

@sio.event
async def seek(sid: str, data: dict):
    await streams[data['stream_id']].set_progress(data['progress'])

@sio.event
async def shuffle(sid: str, data: dict):
    await streams[data['stream_id']].shuffle()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=80, access_log=False)