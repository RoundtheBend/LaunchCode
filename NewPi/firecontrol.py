#!/usr/bin/env python

import struct
import serial
from xbee import ZigBee
import threading
import time
import json
import BaseHTTPServer
import Queue
from datetime import datetime

class XbeeSerial:
	XbeeModules = []
	Cues = {}
	fireQueue = Queue.Queue(1) 
	CuesLock = threading.Lock()
	txEvent = threading.Event()
	def __init__(self, XbeeFile, ser, cueFile):
		self.txEvent.set()
		f = open(cueFile, 'r')
		for line in f:
			line = line.strip().split(',')
			if len(line) == 2:
				self.Cues[int(line[1])] = {'name': line[0], 'adc': 0}

		f = open(XbeeFile, 'r')
		for line in f:
			line = line.strip().split(',')
			if len(line) == 2:
				line[0] = struct.pack('>Q', int(line[0], 16))
				line[1] = struct.pack('>H', int(line[1], 16))
				self.XbeeModules.append((line[0], line[1]))
		self.xbee = ZigBee(ser, callback=self.callback_data)
		t = threading.Thread(target = self.loop)
		t.start()
	
	def loop(self):
		moduleStatus = 0
		while True:
			self.txEvent.wait(3)
			try:
				fireCue = self.fireQueue.get(False)
			except Queue.Empty:
				fireCue = -1
			if fireCue < 0:	
				if moduleStatus >= len(self.XbeeModules):
					moduleStatus = 0
				self.updateStatus(moduleStatus)
				moduleStatus += 1
			else:
				self.fire(fireCue)

	def addFire(self, cue):
		self.fireQueue.put(cue)	

	def fire(self, cue):
		num = cue % 20
		module = cue / 20
		if module >= len(self.XbeeModules):
			return
		print('%s - Fireing cue: %d' % (datetime.now(), cue))
		self.tx(module, '[L%d]' % num)

	def updateStatus(self, module):
		self.tx(module, '[S]')

	def getStatus(self):
		with self.CuesLock:
			return self.Cues 

	def tx(self, module, data):
		self.txEvent.clear()
		self.xbee.tx(dest_addr_long = self.XbeeModules[module][0], dest_addr=self.XbeeModules[module][1], data = data)

	def callback_data(self, data):
		if data['id'] == 'rx':
			self.txEvent.set()
			for (i, module) in enumerate(self.XbeeModules):
				if data['source_addr_long'] == module[0] and data['source_addr'] == module[1]:
					moduleNum = i
					break;
			else:
				print('%s - unknown module' % datetime.today())
				return
			if data['rf_data'][0] != '[':
				status = data['rf_data'].split(',')
				with self.CuesLock:
					for i in range(0, len(status), 2):
						cue = int(status[i]) + 20 * moduleNum
						if cue in self.Cues:
							self.Cues[cue]['adc'] = status[i + 1]
				print('%s - status from module %d' % (datetime.now(), moduleNum))
			else:
				print('%s - response from module %d' % (datetime.now(), moduleNum))
		#else:
		#	print(data)

class jsonServer(BaseHTTPServer.BaseHTTPRequestHandler):
	def goodResponse(self):
		self.send_response(200)
		self.send_header('Content-type', 'application/json')
		self.send_header('Access-Control-Allow-Headers', 'Content-Type')
		self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		self.send_header('Access-Control-Allow-Origin', self.headers.getheader('Origin'))
		self.send_header('Access-Control-Max-Age', '3600')
		self.end_headers()

	def do_OPTIONS(self):
		self.goodResponse()
		 
	def do_GET(self):
		if self.path == '/action/status':
			self.goodResponse()
			self.wfile.write(json.dumps(self.xbeeSerial.getStatus()))
		elif self.path == '/show/status':
			self.goodResponse()
			self.wfile.write(json.dumps(self.show.status()))
		else:
			self.send_error(404)
	def do_POST(self):
		if self.path == '/action/fire':
			content_len = int(self.headers.getheader('content-length', 0))
			post_body = self.rfile.read(content_len)
			try:
				data = json.loads(post_body)
			except ValueError, e:
				data = {}
			if 'cue' in data:
				self.xbeeSerial.addFire(int(data['cue']))
				self.goodResponse()
				self.wfile.write(json.dumps({'fireing': data['cue']}))
			else:
				self.send_error(400)
		elif self.path == '/show/start':
			self.goodResponse()
			self.wfile.write(json.dumps(self.show.start()))
		elif self.path == '/show/eStop':
			self.goodResponse()
			self.wfile.write(json.dumps(self.show.eStop()))
		elif self.path == '/show/reset':
			self.goodResponse()
			self.wfile.write(json.dumps(self.show.reset()))
		else:
			self.send_error(404)

class Show():
	running = threading.Event()
	show = []
	pos = 0
	dataLock = threading.Lock()

	def __init__(self, showFile, xbeeSerial):
		f = open(showFile, 'r')
		for line in f:
			line = line.strip().split(',')
			if len(line) == 2:
				self.show.append((int(line[0]), int(line[1])))
		self.xbeeSerial = xbeeSerial
		t = threading.Thread(target = self.loop)
		t.start()

	def start(self):
		if self.pos >= len(self.show):
			return {'status': 'finished!'}
		else:
			self.running.set()
			return {'status': 'running'} 
		
	def loop(self):
		while True:
			self.running.wait()
			if self.pos >= len(self.show):
				self.running.clear()
			elif self.pos == 0 or time.time() > self.time + self.show[self.pos - 1][1]:
				self.xbeeSerial.addFire(self.show[self.pos][0])
				self.time = time.time()
				with self.dataLock:
					self.pos += 1
			else:
				time.sleep(0.1)
			
	def eStop(self):
		self.running.clear()
		return {'status': 'estop'} 
	
	def reset(self):
		if self.running.is_set():
			return {'message': 'Can\'t reset while running'}
		else:
			self.pos = 0
			return {'message': 'Show reset'}	

	def status(self):
		firedCue = -1
		nextCue = -1
		waitingFor = -1
		status = 'unknown'
		with self.dataLock:
			if self.pos < len(self.show):
				if self.running.is_set():
					status = 'running'
				elif self.pos > 0:
					status = 'estop'
				else:
					status = 'stopped'
				nextCue = self.show[self.pos][0]
				if self.pos > 0:
					firedCue = self.show[self.pos - 1][0]
					waitingFor = self.show[self.pos -1][1]
			else:
				status = 'finished!'
			return {'status': status,
				'firedCue': firedCue,
				'nextCue': nextCue,
				'waitingFor': waitingFor}  

ser = serial.Serial('/dev/ttyAMA0', 9600)

xbeeSerial = XbeeSerial('XbeeModules.txt', ser, 'CueList.txt')

show = Show('Show.txt', xbeeSerial) 

jsonServer.xbeeSerial = xbeeSerial
jsonServer.show = show
httpd = BaseHTTPServer.HTTPServer(('0.0.0.0', 8080), jsonServer)
httpd.serve_forever()

httpd.server_close()
xbeeSerial.xbee.halt()
ser.close()
