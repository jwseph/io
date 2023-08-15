import socketio

import random

WIN_STATES = [
  0b100100100,
  0b010010010,
  0b001001001,
  0b111000000,
  0b000111000,
  0b000000111,
  0b100010001,
  0b001010100,
]

class Game:
    def __init__(self, *players: list[str]):
        self.players = players  # [O, X]
        self.starting_player = self.player = 1
        self.state = 0

    @property
    def winner(self) -> int:
        for win_state in WIN_STATES:
            if self.state>>9 & win_state != win_state: continue
            taken = self.state & win_state
            if taken == 0: return 0
            if taken == win_state: return 1
        return -1

origins = [
    'https://tctct.pages.dev',
    'http://tctct.pages.dev',
    'http://localhost',
]

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app = socketio.ASGIApp(sio, socketio_path='/tictactoe/socket.io')

sid_names: dict[str, str] = {}
name_sids: dict[str, str] = {}
games: dict[str, Game] = {}

@sio.event
async def connect(sid: str, environ: dict):
    print(f'[TTT] {sid} connected')

@sio.event
async def disconnect(sid: str):
    print(f'[TTT] {sid} disconnected')
    del name_sids[sid_names[sid]]
    del sid_names[sid]
    if sid in games:
        game = games[sid]
        sid2 = game.players[1-game.players.index(sid)]
        del game
        await sio.emit('opponent_disconnected', to=sid2)

@sio.event
async def set_name(sid: str, name: str):
    assert name not in name_sids
    sid_names[sid] = name
    name_sids[name] = sid

@sio.event
async def create_game(sid: str, opponent: str):
    assert sid_names[sid] and opponent
    sid2 = name_sids[opponent]
    games[sid] = games[sid2] = Game(sid, sid2)
    names = [sid_names[sid], sid_names[sid2]]
    await sio.emit('start_game', {'you': 0, 'names': names}, to=sid)
    await sio.emit('start_game', {'you': 1, 'names': names}, to=sid2)

@sio.event
async def make_move(sid: str, move: int):
    game = games[sid]
    assert sid == game.players[game.player]
    sid2 = game.players[1-game.player]
    if game.state & 1<<move+9: return
    game.state |= game.player<<move | 1<<move+9
    game.player = 1-game.player
    if game.winner >= 0:
        game.player = game.starting_player = 1-game.starting_player
    await sio.emit('make_move', move, to=sid2)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=80, access_log=False)