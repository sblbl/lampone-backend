from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db
import cups
import base64
from PIL import Image
from io import BytesIO
import time
import os

load_dotenv()
conn = cups.Connection()
printers = conn.getPrinters()
printer = printers['SII_RP-F10_G10']
creds = credentials.Certificate('service-account.json')

def base64_to_image(base64_string):
	# Remove the data URI prefix if present
	if "data:image" in base64_string:
		base64_string = base64_string.split(",")[1]

	# Decode the Base64 string into bytes
	image_bytes = base64.b64decode(base64_string)
	return image_bytes

def create_image_from_bytes(image_bytes):
	# Create a BytesIO object to handle the image data
	image_stream = BytesIO(image_bytes)

	# Open the image using Pillow (PIL)
	image = Image.open(image_stream)
	return image

firebase_admin.initialize_app(creds, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
})


def msg_listener(event):
	print(f'Event type: {event.event_type}')
	print(f'Event path: {event.path}')
	print(f'Data: {event.data}')

def print_listener(event):
	"""
	print(f'Event type: {event.event_type}')
	print(f'Event path: {event.path}')
	print(f'Data: {event.data}')
	"""
	print('new print event')
	# check if the print is not null
	if event.data != '':
		image_bytes = base64_to_image(event.data)
		image = create_image_from_bytes(image_bytes)
		#image.show()
		image.save('print.jpg')
		time.sleep(1)
		conn.printFile('SII_RP-F10_G10', 'print.jpg', 'image', {"fit-to-page": "true"})
		# TODO: set the print to null in firebase
		refPrint.set('')
	else:
		print('No print data')

refMsg = db.reference('/msg')
refPrint = db.reference('/print')

refMsg.listen(msg_listener)
refPrint.listen(print_listener)

try:
	while True:
		time.sleep(1) 
except KeyboardInterrupt:
	print('Listener stopped')