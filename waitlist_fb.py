import firebase_admin
from firebase_admin import credentials, db
import os
import base64

_cert = {
  "type": "service_account",
  "project_id": "waitlist-demo",
  "private_key_id": os.getenv('WAITLIST_PRIVATE_KEY_ID'),
  "private_key": base64.b64decode(os.getenv('WAITLIST_PRIVATE_KEY')).decode(),
  "client_email": "firebase-adminsdk-ao7f7@waitlist-demo.iam.gserviceaccount.com",
  "client_id": "105885587554505259605",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-ao7f7%40waitlist-demo.iam.gserviceaccount.com"
}
app = firebase_admin.initialize_app(
  credentials.Certificate(_cert),
  {'databaseURL': 'https://waitlist-demo-default-rtdb.firebaseio.com/'},
  'waitlist',
)

ref = db.reference('/', app)