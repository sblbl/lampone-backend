from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db
from escpos.printer import Usb
import cups
import base64
from PIL import Image, ImageOps
from io import BytesIO
import re
import time
import os

folder = '/home/sblbl/Desktop/code/lampone/backend/'
print_w = 512

load_dotenv()
conn = cups.Connection()
printers = conn.getPrinters()
printer = printers['SII_RP-F10_G10'] # cups
p = Usb(0x0619, 0x012d, 0, profile="TM-T88III") # escpos
creds = credentials.Certificate(folder + 'service-account.json')

firebase_admin.initialize_app(creds, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
})


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

def parse_format(text, ln=2):
	formatted_parts = re.split(r'(\*\*.*?\*\*|_.*?_)', text)
	for part in formatted_parts:
		if part.startswith('**') and part.endswith('**'):
			p.set(bold=True)
			p.text(part[2:-2])
			p.set_with_default()
		elif part.startswith('_') and part.endswith('_'):
			p.set(underline=1) 
			p.text(part[1:-1])
			p.set(underline=0)
			p.set_with_default()
		else:
			p.text(part)
	p.ln(ln)

def msg_listener(event):
	print(f'msg event: {event.data}')

def text_listener(event):
	print('text event')
	if event.data != '':
		p.ln(2)
		p.set_with_default()
		for i, line in enumerate(event.data):
			if line['image'] == False:
				p.set(align=line['align'])
				# check if last line and if next line is text
				ln = 2
				"""
				if i < len(event.data) - 1 and event.data[i + 1]['image'] == True:
					ln = 4			
				"""
				parse_format(line['text'], ln)
			else:
				image_bytes = base64_to_image(line['text'])
				image = Image.open(BytesIO(image_bytes))
				#get the width and height of the image
				width, height = image.size
				if width > height:
					new_width = 450
					new_height = int(new_width * height / width)
					image = image.resize((new_width, new_height))
					if line['align'] == 'center':
						padding = (print_w - new_width) // 2 
						image = ImageOps.expand(image, (padding, 0, padding, 0), fill='white')
					elif line['align'] == 'right':
						padding = print_w - new_width
						image = ImageOps.expand(image, (padding, 0, 0, 0), fill='white')
					else:
						image = ImageOps.expand(image)
				else:
					new_height = 500
					new_width = int(new_height * width / height)
					if line['align'] == 'center':
						padding = (print_w - new_width) // 2
						image = image.resize((new_width, new_height))
						image = ImageOps.expand(image, (padding, 0, padding, 0), fill='white')
					elif line['align'] == 'right':
						padding = print_w - new_width
						image = image.resize((new_width, new_height))
						image = ImageOps.expand(image, (padding, 0, 0, 0), fill='white')
					else:
						image = image.resize((new_width, new_height))
						image = ImageOps.expand(image)
				p.image(image)
				p.ln(1)
				
		p.ln(2)
		p.cut()
		refText.set('')
	
print_queue = {}

def print_listener(event):
	print('print event')
	if isinstance(event.data, dict) and event.data != {}:
		print_queue = event.data
		# iterate print_queue in order to print the data
		sorted_timestamps = sorted(print_queue.keys())
		for timestamp in sorted_timestamps:
			with open(folder + 'last_timestamp.txt', 'r') as f:
				last_timestamp = int(f.read())
			if int(timestamp) > last_timestamp:
				b64 = print_queue[timestamp]
				image_bytes = base64_to_image(b64)
				image = create_image_from_bytes(image_bytes)
				with open(folder + 'last_timestamp.txt', 'w') as f:
					f.write(timestamp)
				image.save(folder + 'print.png')
				time.sleep(1)
				conn.printFile('SII_RP-F10_G10', folder + 'print.png', 'image', {"fit-to-page": "true"})
		print_queue = {}
		dbVal = refPrint.get()
		print(dbVal)
		if isinstance(dbVal, dict) and dbVal != {}:
			with open(folder + 'last_timestamp.txt', 'r') as f:
				last_timestamp = int(f.read())
			# remove from dbVal the timestamps that are <= last_timestamp
			for timestamp in list(dbVal.keys()):
				if int(timestamp) <= last_timestamp:
					del dbVal[timestamp]
			refPrint.set(dbVal)
		"""
		image_bytes = base64_to_image(event.data)
		image = create_image_from_bytes(image_bytes)
		#image.show(
		image.save(folder + 'print.png')
		time.sleep(1)
		conn.printFile('SII_RP-F10_G10', folder + 'print.png', 'image', {"fit-to-page": "true"})
		refPrint.set('')
		"""
	else:
		print('No print data')

refMsg = db.reference('/msg')
refText = db.reference('/text')
refPrint = db.reference('/print')

refMsg.listen(msg_listener)
refText.listen(text_listener)
refPrint.listen(print_listener)

try:
	while True:
		time.sleep(1) 
except KeyboardInterrupt:
	print('Listener stopped')