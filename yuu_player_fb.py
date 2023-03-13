import firebase_admin
from firebase_admin import credentials, db
import os, base64, json

cert = json.loads(base64.b64decode(os.getenv('YUU_PRIVATE_KEY')).decode())
app = firebase_admin.initialize_app(
  credentials.Certificate(cert),
  {'databaseURL': 'https://yuu-player-default-rtdb.firebaseio.com/'},
  'yuu-player',
)

ref = db.reference('/', app)