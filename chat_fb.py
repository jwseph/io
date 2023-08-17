import firebase_admin
from firebase_admin import credentials, db
import os
import base64

from dotenv import load_dotenv
load_dotenv()

_cert = {
  "type": "service_account",
  "project_id": "kamiak-chat",
  "private_key_id": os.environ['PRIVATE_KEY_ID'],
  "private_key": base64.b64decode(os.environ['PRIVATE_KEY']).decode(),
  "client_email": "firebase-adminsdk-klupx@kamiak-chat.iam.gserviceaccount.com",
  "client_id": "109175298576378518214",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-klupx%40kamiak-chat.iam.gserviceaccount.com"
}
app = firebase_admin.initialize_app(
  credentials.Certificate(_cert),
  {'databaseURL': 'https://kamiak-chat-default-rtdb.firebaseio.com/'},
)

ref = db.reference('/', app)
userinfo_ref = ref.child('users')