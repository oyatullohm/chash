import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

# Ilova ishga tushganda BIR MARTA initsializatsiya qilinadi
if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)


def send_push_notification(firebase_key: str, title: str, body: str):
    """
    Bitta qurilmaga push notification yuboradi.
    firebase_key bo'sh bo'lsa - jim o'tkazib yuboradi (xato bermaydi).
    """
    if not firebase_key:
        return

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=firebase_key,
    )
    messaging.send(message)