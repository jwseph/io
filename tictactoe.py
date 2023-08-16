import socketio

import random

O, X = 0, 1

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
    def __init__(self, o_sid: str, x_sid: str):
        self.players = [o_sid, x_sid]
        self.player = self.starting_player = 1
        self.state = 0
    
    def reset(self):
        self.player = self.starting_player = 1-self.starting_player
        self.state = 0
    
    def get_opponent(self, sid: str) -> str:
        return self.players[1-self.players.index(sid)]

    @property
    def winner(self) -> int:
        for win_state in WIN_STATES:
            if self.state>>9 & win_state != win_state: continue
            taken = self.state & win_state
            if taken == 0: return 0
            if taken == win_state: return 1
        return -1
    
    @property
    def over(self) -> bool:
        full = (1<<9)-1<<9
        return self.state & full == full or self.winner >= 0

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
waiting: list[str] = []

async def remove_name(sid: str):
    if sid not in sid_names: return
    if waiting == [sid]: waiting.pop()
    del name_sids[sid_names[sid].lower()]
    del sid_names[sid]
    if sid in games:
        game = games[sid]
        sid2 = game.get_opponent(sid)
        del game
        await sio.emit('opponent_disconnected', to=sid2)

@sio.event
async def connect(sid: str, environ: dict):
    print(f'[TTT] {sid} connected')

@sio.event
async def disconnect(sid: str):
    print(f'[TTT] {sid} disconnected')
    await remove_name(sid)

@sio.event
async def set_name(sid: str, name: str):
    name = name.strip()
    assert name and name.lower() not in name_sids
    if sid in sid_names:
        del name_sids[sid_names[sid].lower()]
    sid_names[sid] = name
    name_sids[name.lower()] = sid

    if waiting == [sid]: return
    if not waiting:
        waiting.append(sid)
        return

    # Start game if someone else was waiting
    o_sid, x_sid = sid, waiting[0]
    waiting.pop()
    if random.randint(0, 1):
        o_sid, x_sid = x_sid, o_sid
    games[o_sid] = games[x_sid] = Game(o_sid, x_sid)
    names = [sid_names[o_sid], sid_names[x_sid]]
    await sio.emit('start_game', {'you': O, 'names': names}, to=o_sid)
    await sio.emit('start_game', {'you': X, 'names': names}, to=x_sid)

@sio.event
async def clear_name(sid: str):
    await remove_name(sid)

@sio.event
async def make_move(sid: str, move: int):
    game = games[sid]
    if game.over: return
    assert sid == game.players[game.player]
    sid2 = game.players[1-game.player]
    if game.state & 1<<move+9: return
    game.state |= game.player<<move | 1<<move+9
    game.player = 1-game.player
    await sio.emit('make_move', move, to=sid2)

@sio.event
async def rematch(sid: str):
    game = games[sid]
    if not game.over: return
    game.reset()
    sid2 = game.get_opponent(sid)
    await sio.emit('reset_board', to=sid2)
    await sio.emit('reset_board', to=sid)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=80, access_log=False)