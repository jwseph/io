import chat
import battleship
# import twentyfour


app = chat.app
app.other_asgi_app = battleship.app
# battleship.app.other_asgi_app = twentyfour.app


if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=80)


from uvicorn import workers
class CustomUvicornWorker(workers.UvicornWorker):
  CONFIG_KWARGS = {'ws': 'websockets', 'ws_max_size': 100*1024*1024+1000}