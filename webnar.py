import os
import sys
import socket
import subprocess
import datetime

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.httpclient

class CommandDataStore(object):
	_instance = None

	def __init__(self):
		self.data = {}

	@classmethod
	def instance(cls):
		if cls._instance is None:
			cls._instance = cls()
		return cls._instance
	
	def set(self, cmd, value):
		self.data[cmd] = (datetime.datetime.now(), value)

	def values(self):
		return self.data.iteritems()

class MainHandler(tornado.web.RequestHandler):
	def get(self):
		store = CommandDataStore.instance()
		for cmd, (time, data) in store.values():
			self.write("%s: %r  (updated %r)<br>" % (cmd, data, time))
			
application = tornado.web.Application([
	(r"/", MainHandler),
])

def main():
	"""docstring for main"""
	tornado.ioloop.IOLoop.instance().start()

def watch_command(cmd, interval, io_loop=None):
	running = False
	def handle_interval():
		if running:
			return
		
		checker = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	
		def handle_events(fd, events):
			if events & io_loop.ERROR:
				if checker.poll() is None:
					raise Exception("not done ?")
				else:
					io_loop.remove_handler(checker.stdout.fileno())

			if events & io_loop.READ:
				output = checker.stdout.read()
				lines = output.split('\n')
				CommandDataStore.instance().set(cmd, lines[-1])
		
			return

		io_loop.add_handler(checker.stdout.fileno(), handle_events, io_loop.READ)
	
	return tornado.ioloop.PeriodicCallback(handle_interval, interval, io_loop=io_loop)

if __name__ == '__main__':
	http_server = tornado.httpserver.HTTPServer(application)
	http_server.listen(8888)

	io_loop = tornado.ioloop.IOLoop.instance()

	scheduler = watch_command("ssh batch2 \"curl -w \\\"%{time_connect} %{time_starttransfer} %{time_total} (%{http_code})\\\" -s -o /dev/null http://www.yelp.ie/\"", 5000, io_loop)
	scheduler.start()
	
	io_loop.start()