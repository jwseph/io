import uvicorn
import chat
# import battleship


app = chat.app
# app.other_asgi_app = battleship.app


class CustomUvicornWorker(uvicorn.workers.UvicornWorker):
  CONFIG_KWARGS = {'ws': 'websockets', 'ws_max_size': 100*1024*1024}


if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=80)