from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db
import time
import os

load_dotenv()

creds = credentials.Certificate('service-account.json')


firebase_admin.initialize_app(creds, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
})


def msg_listener(event):
	print(f'Event type: {event.event_type}')
	print(f'Event path: {event.path}')
	print(f'Data: {event.data}')

def print_listener(event):
	#print(f'Event type: {event.event_type}')
	#print(f'Event path: {event.path}')
	#print(f'Data: {event.data}')
	print('new print event')

refMsg = db.reference('/msg')
refPrint = db.reference('/print')

refMsg.listen(msg_listener)
refPrint.listen(print_listener)

try:
	while True:
		time.sleep(1) 
except KeyboardInterrupt:
	print('Listener stopped')