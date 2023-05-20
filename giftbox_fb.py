import firebase_admin
from firebase_admin import credentials, db
import os
import base64

_cert = {
  "type": "service_account",
  "project_id": "giftbox-demo",
  "private_key_id": os.getenv('GIFTBOX_PRIVATE_KEY_ID'),
  "private_key": base64.b64decode(os.getenv('GIFTBOX_PRIVATE_KEY')).decode(),
  "client_email": "firebase-adminsdk-k1n2l@giftbox-demo.iam.gserviceaccount.com",
  "client_id": "111970856790361137626",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-k1n2l%40giftbox-demo.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
app = firebase_admin.initialize_app(
  credentials.Certificate(_cert),
  {'databaseURL': 'https://giftbox-demo-default-rtdb.firebaseio.com/'},
  'giftbox',
)

ref = db.reference('/', app)