import chat
# import battleship


app = chat.app
# app.other_asgi_app = battleship.app


if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=80)