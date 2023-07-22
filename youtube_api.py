import aiohttp
import os
import json

from dotenv import load_dotenv
load_dotenv()

def parse_duration(text: str) -> int:
  text = text.split('T')[-1]
  res, cur = 0, 0
  for ch in text:
    match ch:
      case 'H': res += cur*3600
      case 'M': res += cur*60
      case 'S': res += cur
    if not ch.isdigit():
      cur = 0
      continue
    cur = cur*10 + int(ch)
  return res
    

class YoutubeAPI:
  WHAP = 'PLEHRHjICEfDVlP4J7Zn1_LFTm_-8bkxpN'
  NICE = 'PLz6c16Y2dQeOm1hl_oY5bRDBO5Ni-IiP5'

  def __init__(self, *, api_key: str = os.getenv('YOUTUBE_API_KEY'), url='https://youtube.googleapis.com/youtube/v3/'):
    self._key = api_key
    self._url = url
  
  async def _get_playlist_info(self, s, playlist_id: str):
    r = await s.get(url=self._url+'playlists', params={
      'key': self._key,
      'id': playlist_id,
      'part': 'snippet'
    })
    return await r.json()

  async def _get_video_ids(self, s, playlist_id: str, page_token: str = ''):
    r = await s.get(self._url+'playlistItems', params={
      'key': self._key,
      'playlistId': playlist_id,
      'pageToken': page_token,
      'part': 'contentDetails',
      'maxResults': 50,
      'fields': 'nextPageToken,items/contentDetails/videoId',
    })
    return await r.json()
  
  async def _get_video_info(self, s, video_ids_cs: list, page_token: str = ''):
    r = await s.get(self._url+'videos', params={
      'key': self._key,
      'id': video_ids_cs,
      'pageToken': page_token,
      # 'part': 'contentDetails',
      # 'fields': 'items/contentDetails/duration',
      'part': 'snippet,contentDetails',
      'fields': ','.join('items/snippet/'+_ for _ in ['channelId', 'title', 'description', 'thumbnails/medium/url', 'thumbnails/standard/url', 'thumbnails/maxres/url', 'tags', 'channelTitle'])+',items/contentDetails/duration,nextPageToken',
    })
    video_infos = (await r.json())['items']
    if len(video_infos) != len(video_ids_cs) and video_infos:
      print('[ERROR] Videos request returned a different length!', video_ids_cs, len(video_infos))
      promises = [self._get_video_info(s, [video_id]) for video_id in video_ids_cs]
      return sum([list(await promise) for promise in promises], [])
    return zip(video_ids_cs, video_infos)
  
  async def get_video_info(self, s, video_ids_cs: list, page_token: str = ''):
    raw_videos = await self._get_video_info(s, video_ids_cs, page_token)
    return {
      video_id: {
        'video_url': 'https://youtu.be/'+video_id,
        'thumbnails': {
          'small': snippet['thumbnails']['medium']['url'],
          'large': snippet['thumbnails']['maxres']['url'] if 'maxres' in snippet['thumbnails'] else snippet['thumbnails']['high']['url'] if 'high' in snippet['thumbnails'] else snippet['thumbnails']['medium']['url'],
        },
        'title': snippet['title'],
        'description': snippet['description'],
        'channel': snippet['channelTitle'],
        'channel_url': 'https://www.youtube.com/channel/'+snippet['channelId'],
        'duration': parse_duration(video['contentDetails']['duration']),
      }
      for video_id, video in raw_videos
      for snippet in [video['snippet']]
    }

  async def _get_playlist_items(self, s, playlist_id: str, excluded_video_ids: set):
    data = await self._get_video_ids(s, playlist_id)
    video_ids = video_queue = [_['contentDetails']['videoId'] for _ in data['items']]
    coros = []
    
    while 'nextPageToken' in data:
      data = await self._get_video_ids(s, playlist_id, page_token=data['nextPageToken'])
      new_video_ids = [_['contentDetails']['videoId'] for _ in data['items']]
      video_ids.extend(new_video_ids)
      video_queue.extend(set(new_video_ids) - excluded_video_ids)
      while len(video_queue) >= 5:
        coros.append(self.get_video_info(s, video_queue[:5]))
        video_queue = video_queue[5:]

    while video_queue:
      coros.append(self.get_video_info(s, video_queue[:5]))
      video_queue = video_queue[5:]
    
    return {
      video_id: video
      for coro in coros
      for video_id, video in (await coro).items()
    }

  async def get_playlist_info(self, playlist_id: str):
    async with aiohttp.ClientSession() as s:
      playlist_info = (await self._get_playlist_info(s, playlist_id))['items'][0]['snippet']
    return {
      'title': playlist_info['title'],
      'description': playlist_info['description'],
      'thumbnails': {
        'small': playlist_info['thumbnails']['medium']['url'],
        'large': playlist_info['thumbnails']['maxres']['url'] if 'maxres' in playlist_info['thumbnails'] else playlist_info['thumbnails']['high']['url'] if 'high' in playlist_info['thumbnails'] else playlist_info['thumbnails']['medium']['url'],
      },
      'url': f'https://www.youtube.com/playlist?list={playlist_id}',
      'channel': playlist_info['channelTitle'],
      'channel_url': 'https://www.youtube.com/channel/'+playlist_info['channelId'],
    }

  async def get_playlist(self, playlist_id: str, excluded_video_ids: set = set()):
    info_coro = self.get_playlist_info(playlist_id)
    async with aiohttp.ClientSession() as s:
      videos = await self._get_playlist_items(s, playlist_id, excluded_video_ids)
    
    return (await info_coro) | {
      'videos': videos,
      'video_ids': dict.fromkeys(videos, True),
    }

  async def get_channel_info(self, channel_url: str) -> dict:
    # This function is so scuffed---I didn't want to use API calls
    async with aiohttp.ClientSession() as s:
      r = await s.get(channel_url)
      text = await r.text()
    res = {}
    i = text.index('"width":48,')
    l, r = text.rfind('{', 0, i), text.find('}', i)+1
    res['image'] = json.loads(text[l:r])['url']

    l = text.index('{', text.index('subscriberCountText'))
    r = l+1
    depth = 1
    while depth:
      if text[r] == '{': depth += 1
      if text[r] == '}': depth -= 1
      r += 1
    res['subscribers'] = json.loads(text[l:r])['simpleText']
    return res