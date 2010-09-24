import os
import sys
import socket
import subprocess
import datetime

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.httpclient

STAT_OK = "ok"
STAT_WARNING = "warning"
STAT_CRITICAL = "critical"

watch_stats = []

class StatWatcher(object):
    interval = 1000
    command = None

    def __init__(self):
        self._last_updated = None
        self._status = STAT_OK

    def handle_output(self, output):
        self._last_updated = datetime.datetime.now()

    @property
    def value(self):
        pass
        
    @property
    def last_updated(self):
        return self._last_updated
    
    @property
    def status(self):
        return self._status

    def add_to_loop(self, io_loop=None):
        running = False
        def handle_interval():
            if running:
                return

            checker = subprocess.Popen(self.command, shell=True, stdout=subprocess.PIPE)

            def handle_events(fd, events):
                if events & io_loop.ERROR:
                    if checker.poll() is None:
                        raise Exception("not done ?")
                    else:
                        io_loop.remove_handler(checker.stdout.fileno())

                if events & io_loop.READ:
                    output = checker.stdout.read()
                    self.handle_output(output)

                return

            io_loop.add_handler(checker.stdout.fileno(), handle_events, io_loop.READ)

        tornado.ioloop.PeriodicCallback(handle_interval, self.interval, io_loop=io_loop).start()


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        global watch_stats
        for stat_watcher in watch_stats:
            self.write("%s: %s (%s)" % (stat_watcher.name, stat_watcher.value, stat_watcher.status))
