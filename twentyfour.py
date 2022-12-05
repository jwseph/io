# https://www.4nums.com/solutions/allsolvables//
# ×
# STOP USING SIO ROOMS
import json
import socketio
import random
import re


class Fraction:
    def __init__(self, n: int, d: int=1):
        assert d != 0
        if d < 0:
            n = -n
            d = -d
        self.n = n
        self.d = d
        self.simplify()

    def simplify(self):
        f = Fraction.gcd(self.n, self.d)
        self.n //= f
        self.d //= f

    @staticmethod
    def gcd(a, b):
        a, b = abs(a), abs(b)
        while b: a, b = b, a%b
        return a

    @staticmethod
    def eval(expr: str):
        if expr.isnumeric(): return Fraction(int(expr))
        assert expr[0]+expr[-1] == '()'
        i, p = 0, 0  # p is parenthesis level
        while i < len(expr):
            if expr[i] == '(': p += 1
            if expr[i] == ')': p -= 1
            if p == 1 and expr[i] == ' ': break
            i += 1
        assert i < len(expr)
        l_str, op, r_str = expr[1:i], expr[i+1], expr[i+3:-1]
        assert op in '+-*/'
        l = Fraction.eval(l_str)
        r = Fraction.eval(r_str)
        return eval(f'l{op}r')

    def __repr__(self):
        if self.d == 1: return f"{self.n}"
        return f"{self.n}/{self.d}"

    def __mul__(self, other):
        return Fraction(self.n*other.n, self.d*other.d)
    
    def __truediv__(self, other):
        return Fraction(self.n*other.d, self.d*other.n)
    
    def __add__(self, other):
        return Fraction(self.n*other.d+other.n*self.d, self.d*other.d)
    
    def __sub__(self, other):
        return Fraction(self.n*other.d-other.n*self.d, self.d*other.d)
    
    def __eq__(self, other):
        return self.n == other.n and self.d == other.d


solutions = json.load(open('24_solutions.json'))
lobby_ids = [_ for _ in open('24_words.txt').read().split('\n') if _]

def pick_lobby_id() -> str:
    res = random.choice(lobby_ids)
    lobby_ids.remove(res)
    return res

async def update_lobby(lobby):
    await sio.emit('update_lobby', {'lobby': lobby}, to=lobby['lobby_id'])

async def reset_numbers(lobby):
    lobby['started'] = True
    numbers_str = random.choice(list(solutions))
    lobby['numbers'] = list(map(int, numbers_str.split()))
    random.shuffle(lobby['numbers'])
    if 'solutions' in lobby: del lobby['solutions']
    await update_lobby(lobby)

def get_lobby(data):
    return lobbies[data['lobby_id']]

def is_lobby_host(sid, lobby):
    return lobby['users'][0] == sid

async def add_to_lobby(sid, lobby):
    assert sid not in lobby['users']
    print(lobby)
    lobby['users'].append(sid)
    if lobby['started']: lobby['user_scores'][sid] = 0
    sio.enter_room(sid, lobby['lobby_id'])
    await update_lobby(lobby)

async def remove_from_lobby(sid, lobby):
    lobby_id = lobby['lobby_id']
    lobby['users'].remove(sid)
    if lobby['started']:
        del lobby['user_scores'][sid]
    print(lobby)
    sio.leave_room(sid, lobby_id)
    if not lobby['users']:
        del lobbies[lobby_id]
        return
    await update_lobby(lobby)


origins = [
  'https://kamiak.org',
  'https://beta.kamiak.org',
  'https://kamiakhs.github.io',
  'https://battleship.kamiak.org',
  'http://localhost',
]
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=origins)
app = socketio.ASGIApp(sio, socketio_path='/24/socket.io')

lobbies = {}


@sio.event
async def connect(sid, environ):
    print(sid, 'connected')

@sio.event
async def disconnect(sid):
    print(sid, 'disconnected')
    rooms = sio.rooms(sid)
    lobby_ids = set(rooms)-{sid}
    for lobby in map(lobbies.get, lobby_ids):
        await remove_from_lobby(sid, lobby)

@sio.event
async def create_lobby(sid):
    print('create_lobby', sid)
    lobby_id = pick_lobby_id()
    lobby = lobbies[lobby_id] = {
        'name': lobby_id.title(),
        'lobby_id': lobby_id,
        'started': False,
        'users': [],
    }
    await add_to_lobby(sid, lobby)

@sio.event
async def join_lobby(sid, data):
    print('join_lobby', sid)
    print(list(lobbies))
    print(f"'{data['lobby_id']}'")
    lobby = get_lobby(data)
    await add_to_lobby(sid, lobby)

@sio.event
async def leave_lobby(sid, data):
    print('leave_lobby', sid)
    await remove_from_lobby(sid, get_lobby(data))

@sio.event
async def start_lobby(sid, data):
    print('start_lobby', sid)
    lobby = get_lobby(data)
    assert is_lobby_host(sid, lobby)
    lobby['user_scores'] = dict.fromkeys(lobby['users'], 0)
    await reset_numbers(lobby)

@sio.event
async def submit_solution(sid, data):
    print('submit_solution', sid)
    expr = data['solution']
    lobby = get_lobby(data)
    assert len(expr) <= len('(((13 + 13) + 13) + 13)'), 'Expression must not be too long'
    numbers = list(map(int, re.findall(r'-?\d+', expr)))
    assert sorted(numbers) == sorted(lobby['numbers']), 'Numbers in solution must be the same as the numbers for the current round'
    assert all(1 <= _ <= 13 for _ in numbers), 'All numbers must be integers within [1, 13]'
    assert Fraction.eval(expr) == Fraction(24), 'Solution must evaluate to 24'
    lobby['solutions'] = solutions[' '.join(lobby['numbers'])]
    await update_lobby(lobby)

@sio.event
async def next_lobby_round(sid, data):
    print('next_lobby', sid)
    lobby = get_lobby(data)
    assert is_lobby_host(sid, lobby)
    await reset_numbers(lobby)
    

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)