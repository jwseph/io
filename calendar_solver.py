from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from datetime import datetime, timezone, timedelta
from functools import lru_cache

def reflect(r, c, i):
    return [(r, c), (3-r, c), (r, 3-c), (3-r, 3-c)][i]

def rotate(r, c, i):
    return [(r, c), (3-c, r), (3-r, 3-c), (c, 3-r)][i]

def find_reflections(coords):
    return [[reflect(r, c, i) for r, c in coords] for i in range(4)]

def find_rotations(coords):
    return [[rotate(r, c, i) for r, c in coords] for i in range(4)]

def find_transformations(coords):
    tfs = set()
    for rotation in find_rotations(coords):
        for tf in find_reflections(rotation):
            for u in range(4):
                for l in range(4):
                    tfs.add(tuple(sorted((r-u, c-l) for r, c in tf)))
    return list(map(list, tfs))

R, C = 8, 7
PIECES = [
    [(0, 0), (1, 0), (2, 0), (1, 1), (1, 2)],  # T
    [(0, 0), (1, 0), (2, 0), (3, 0), (3, 1)],  # ----v
    [(0, 0), (1, 0), (2, 0), (3, 0)],  # ----
    [(0, 0), (1, 0), (2, 0), (2, 1)],  # L
    [(0, 0), (1, 0), (1, 1), (2, 1)],  # -|^
    [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)],  # L_
    [(0, 0), (1, 0), (2, 0), (2, 1), (3, 1)],  # --v_
    [(0, 0), (1, 0), (2, 0), (2, 1), (0, 1)],  # [
    [(0, 0), (1, 0), (1, 1), (1, 2), (2, 2)],  # ]_
    [(0, 0), (1, 0), (2, 0), (2, 1), (1, 1)],  # b
]
PIECES_TRANSFORMED = [find_transformations(piece) for piece in PIECES]
IDX = {
    'JAN': 0, 'FEB': 1, 'MAR': 2, 'APR': 3, 'MAY': 4, 'JUN': 5,
    'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12,
    '1': 14, '2': 15, '3': 16, '4': 17, '5': 18, '6': 19, '7': 20,
    '8': 21, '9': 22, '10': 23, '11': 24, '12': 25, '13': 26, '14': 27,
    '15': 28, '16': 29, '17': 30, '18': 31, '19': 32, '20': 33, '21': 34,
    '22': 35, '23': 36, '24': 37, '25': 38, '26': 39, '27': 40, '28': 41,
    '29': 42, '30': 43, '31': 44, 'SUN': 45, 'MON': 46, 'TUE': 47, 'WED': 48,
    'THU': 53, 'FRI': 54, 'SAT': 55,
}

@lru_cache(1)
def solve(date: str):
    '''Input format: OCT 6 FRI'''
    vst = [[0]*C for r in range(R)]
    for i in [6, 13, 49, 50, 51, 52]:
        vst[i//C][i%C] = 101
    for arg in date.upper().split():
        i = IDX[arg]
        vst[i//C][i%C] = 100
    used = [False]*len(PIECES)
    def dfs(r, c):
        if r == R: return True
        if c == C: return dfs(r+1, 0)
        if vst[r][c]: return dfs(r, c+1)
        for p, pieces in enumerate(PIECES_TRANSFORMED):
            if used[p]: continue
            used[p] = True
            for piece in pieces:
                if not all(0 <= r+dr < R and 0 <= c+dc < C and not vst[r+dr][c+dc]
                           for dr, dc in piece):
                    continue
                for dr, dc in piece:
                    vst[r+dr][c+dc] = 200+p+1
                if vst[r][c] and dfs(r, c+1): return True
                for dr, dc in piece:
                    vst[r+dr][c+dc] = 0
            used[p] = False
        return False
    dfs(0, 0)
    return vst

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
    tz = timezone(timedelta(hours=-8))
    date = datetime.now(tz).strftime('%b %d %a')
    return solve(date)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='localhost', port=80)