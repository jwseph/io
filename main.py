from fastapi import FastAPI
from dotenv import load_dotenv
load_dotenv()

import chat
import battleship
import twentyfour
import waitlist
import yuu_player
import giftbox
import yuu_player_share

app = FastAPI()

app.mount('/waitlist', waitlist.app)
app.mount('/giftbox', giftbox.app)
app.mount('/yuu', yuu_player.app)
app.mount('/', twentyfour.app)
twentyfour.app.other_asgi_app = battleship.app
battleship.app.other_asgi_app = yuu_player_share.app
yuu_player_share.app.other_asgi_app = chat.app



if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='127.0.0.1', port=80)


from uvicorn import workers
class CustomUvicornWorker(workers.UvicornWorker):
  CONFIG_KWARGS = {'ws': 'websockets', 'ws_max_size': 100*1024*1024+1000}