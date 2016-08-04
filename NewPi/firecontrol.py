#!/usr/bin/env python

from xbee import ZigBee
import threading
import time
import json
import BaseHTTPServer
import Queue
from datetime import datetime
import os
import posixpath
import urllib
import sys
import shutil
import mimetypes
from collections import OrderedDict

class XbeeSerial:
	XbeeModules = OrderedDict()
	#Cues = {}
	#fireQueue = Queue.Queue(1)
	ModulesLock = threading.Lock()
	#CuesLock = threading.Lock()
	#txEvent = threading.Event()
	def __init__(self, ser):
		#self.txEvent.set()
		#f = open(cueFile, 'r')
		#for line in f:
			#line = line.strip().split(',')
			#if len(line) == 2:
				#self.Cues[int(line[1])] = {'name': line[0], 'adc': 0}

		#f = open(XbeeFile, 'r')
		#for line in f:
			#line = line.strip().split(',')
			#if len(line) == 2:
				#line[0] = struct.pack('>Q', int(line[0], 16))
				#line[1] = struct.pack('>H', int(line[1], 16))
				#self.XbeeModules.append((line[0], line[1]))
		self.xbee = ZigBee(ser, callback=self.callback_data)
		#t = threading.Thread(target = self.loop)
		#t.start()

	#def loop(self):
		#moduleStatus = 0
		#while True:
			#self.txEvent.wait(3)
			#try:
				#fireCue = self.fireQueue.get(False)
			#except Queue.Empty:
				#fireCue = -1
			#if fireCue < 0:
				#pass
				#if moduleStatus >= len(self.XbeeModules):
				#	moduleStatus = 0
				#self.updateStatus(moduleStatus)
				#moduleStatus += 1
			#else:
				#self.fire(fireCue)

	def initialize(self):
		with self.ModulesLock:
			self.XbeeModules = OrderedDict()
		self.xbee.at(command = 'ND')
		return {'message': 'Initializing...'}

	def getBoardInfo(self, addr_long, addr):
		#print('Getting board info {0} {1}'.format(addr_long, addr))
		self.tx_addr(addr_long, addr, 'i')

	#def addFire(self, cue):
	#	self.fireQueue.put(cue)

	def fire(self, cue):
		with self.ModulesLock:
			for i, (board_id, (addr_long, addr, num_cues)) in enumerate(self.XbeeModules.iteritems()):
				if cue < num_cues:
					board = board_id
					break
				else:
					cue -= num_cues
			else:
				return

		print('%s - Fireing cue: %d on board: %d' % (datetime.now(), cue, board))
		self.tx_board(board, 'f%c' % cue)

	#def getStatus(self):
		#with self.CuesLock:
			#return self.Cues

	def getStatus(self):
		cues=[]
		with self.ModulesLock:
			for i, (board_id, (addr_long, addr, num_cues)) in enumerate(self.XbeeModules.iteritems()):
				for cue in range(0, num_cues):
					cues.append({'name': 'Board: %d, Cue: %d' % (board_id, cue), 'adc': 500});
		return cues

	def tx_board(self, board, data):
		with self.ModulesLock:
			self.tx_addr(self.XbeeModules[board][0], self.XbeeModules[board][1], data)

	def tx_addr(self, addr_long, addr, data):
		#self.txEvent.clear()
		self.xbee.tx(dest_addr_long = addr_long, dest_addr = addr, data = data)

	def callback_data(self, data):
		if data['id'] == 'rx':
			if len(data['rf_data']) > 0:
				if data['rf_data'][0] == 'I' and len(data['rf_data']) == 3:
					#print('board_id: {0} 64: {1} 16: {2} cues: {3}'.format(ord(data['rf_data'][1]), data['source_addr_long'], data['source_addr'], ord(data['rf_data'][2])))
					with self.ModulesLock:
						self.XbeeModules[ord(data['rf_data'][1])] = (data['source_addr_long'], data['source_addr'], ord(data['rf_data'][2]))
						self.XbeeModules = OrderedDict(sorted(self.XbeeModules.items()))
					#print(self.XbeeModules)
				#else:
					#print(data)
			#self.txEvent.set()
			#for (i, module) in enumerate(self.XbeeModules):
				#if data['source_addr_long'] == module[0] and data['source_addr'] == module[1]:
					#moduleNum = i
					#break;
			#else:
				#print('%s - unknown module' % datetime.today())
				#return
			#if data['rf_data'][0] != '[':
				#status = data['rf_data'].split(',')
				#with self.CuesLock:
					#for i in range(0, len(status), 2):
						#cue = int(status[i]) + 20 * moduleNum
						#if cue in self.Cues:
							#self.Cues[cue]['adc'] = status[i + 1]
				#print('%s - status from module %d' % (datetime.now(), moduleNum))
			#else:
				#print('%s - response from module %d' % (datetime.now(), moduleNum))
		elif data['id'] == 'at_response' and data['command'] == 'ND':
			#print(data)
			if data['parameter']['device_type'] == '\x01':
				self.getBoardInfo(data['parameter']['source_addr_long'], data['parameter']['source_addr'])
		#else:
			#print(data)

class httpServer(BaseHTTPServer.BaseHTTPRequestHandler):
	def goodResponse(self):
		self.send_response(200)
		self.send_header('Content-type', 'application/json')
		#self.send_header('Access-Control-Allow-Headers', 'Content-Type')
		#self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
		#self.send_header('Access-Control-Allow-Origin', self.headers.getheader('Origin'))
		#self.send_header('Access-Control-Max-Age', '3600')
		self.end_headers()

	#def do_OPTIONS(self):
	#	self.goodResponse()

	def do_GET(self):
		if self.path == '/action/status':
			self.goodResponse()
			self.wfile.write(json.dumps(self.xbeeSerial.getStatus()))
		elif self.path == '/show/status':
			self.goodResponse()
			self.wfile.write(json.dumps(self.show.status()))
		else:
			f = self.send_head()
			if f:
				self.copyfile(f, self.wfile)
				f.close()

	def do_POST(self):
		if self.path == '/action/fire':
			content_len = int(self.headers.getheader('content-length', 0))
			post_body = self.rfile.read(content_len)
			try:
				data = json.loads(post_body)
			except ValueError, e:
				data = {}
			if 'cue' in data:
				self.xbeeSerial.fire(int(data['cue']))
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
		elif self.path == '/action/initialize':
			self.goodResponse()
			self.wfile.write(json.dumps(self.xbeeSerial.initialize()))
		else:
			self.send_error(404)

	def send_head(self):
		"""Common code for GET and HEAD commands.
		This sends the response code and MIME headers.
		Return value is either a file object (which has to be copied
		to the outputfile by the caller unless the command was HEAD,
		and must be closed by the caller under all circumstances), or
		None, in which case the caller has nothing further to do.
		"""
		path = self.translate_path(self.path)
		f = None
		if os.path.isdir(path):
			if not self.path.endswith('/'):
				# redirect browser - doing basically what apache does
				self.send_response(301)
				self.send_header("Location", self.path + "/")
				self.end_headers()
				return None
			for index in "index.html", "index.htm":
				index = os.path.join(path, index)
				if os.path.exists(index):
					path = index
					break
			else:
#				 return self.list_directory(path)
				self.send_error(404, "File not found")
				return None
		ctype = self.guess_type(path)
		try:
			# Always read in binary mode. Opening files in text mode may cause
			# newline translations, making the actual size of the content
			# transmitted *less* than the content-length!
			f = open(path, 'rb')
		except IOError:
			self.send_error(404, "File not found")
			return None
		self.send_response(200)
		self.send_header("Content-type", ctype)
		fs = os.fstat(f.fileno())
		self.send_header("Content-Length", str(fs[6]))
		self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
		self.end_headers()
		return f

	def translate_path(self, path):
		"""Translate a /-separated PATH to the local filename syntax.
		Components that mean special things to the local file system
		(e.g. drive or directory names) are ignored.	(XXX They should
		probably be diagnosed.)
		"""
		# abandon query parameters
		path = path.split('?',1)[0]
		path = path.split('#',1)[0]
		path = posixpath.normpath(urllib.unquote(path))
		words = path.split('/')
		words = filter(None, words)
		path = os.getcwd()
		for word in words:
			drive, word = os.path.splitdrive(word)
			head, word = os.path.split(word)
			if word in (os.curdir, os.pardir): continue
			path = os.path.join(path, word)
		return path

	def copyfile(self, source, outputfile):
		"""Copy all data between two file objects.
		The SOURCE argument is a file object open for reading
		(or anything with a read() method) and the DESTINATION
		argument is a file object open for writing (or
		anything with a write() method).
		The only reason for overriding this would be to change
		the block size or perhaps to replace newlines by CRLF
		-- note however that this the default server uses this
		to copy binary data as well.
		"""
		shutil.copyfileobj(source, outputfile)

	def guess_type(self, path):
		"""Guess the type of a file.
		Argument is a PATH (a filename).
		Return value is a string of the form type/subtype,
		usable for a MIME Content-type header.
		The default implementation looks the file's extension
		up in the table self.extensions_map, using application/octet-stream
		as a default; however it would be permissible (if
		slow) to look inside the data to make a better guess.
		"""

		base, ext = posixpath.splitext(path)
		if ext in self.extensions_map:
			return self.extensions_map[ext]
		ext = ext.lower()
		if ext in self.extensions_map:
			return self.extensions_map[ext]
		else:
			return self.extensions_map['']

	if not mimetypes.inited:
		mimetypes.init() # try to read system mime.types
	extensions_map = mimetypes.types_map.copy()
	extensions_map.update({
		'': 'application/octet-stream', # Default
		'.py': 'text/plain',
		'.c': 'text/plain',
		'.h': 'text/plain',
		})

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
				self.xbeeSerial.fire(self.show[self.pos][0])
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

if __name__ == "__main__":
	import serial

	os.chdir(os.path.dirname(sys.argv[0]))

	ser = serial.Serial('/dev/ttyAMA0', 9600)

	xbeeSerial = XbeeSerial(ser)

	show = Show('Show.txt', xbeeSerial)

	os.chdir('www')
	httpServer.xbeeSerial = xbeeSerial
	httpServer.show = show
	httpd = BaseHTTPServer.HTTPServer(('0.0.0.0', 80), httpServer)
	httpd.serve_forever()

	httpd.server_close()
	xbeeSerial.xbee.halt()
	ser.close()
