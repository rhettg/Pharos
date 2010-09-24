import os
import sys
import errno
import signal
import socket
import subprocess
import datetime
import logging

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.httpclient

STAT_OK = "ok"
STAT_WARNING = "warning"
STAT_CRITICAL = "critical"

DEFAULT_INTERVAL = 2000  # In milliseconds

log = logging.getLogger('pharos')

def plural_it(value, singular, plural):
    return singular if value == 1 else plural
    
def format_timedelta(delta):
    secs = delta.seconds
    days = delta.days

    if days:
        return ' '.join((str(days), plural_it(days, "day", "days")))
    if secs >= 60*60:
        num_hours = secs // (60*60)
        return ' '.join((str(num_hours), plural_it(num_hours, "hour", "hours")))
    if secs >= 60:
        num_mins = secs // 60
        return ' '.join((str(num_mins), plural_it(num_mins, "minute", "minutes")))

    return "a moment"


class MetricWatcher(object):
    """base interface for what pharos will use to collect and monitor metrics"""

    def __init__(self, name=None):
        self.name = name

    @property
    def status(self):
        """Returns one of our STAT_* constants to indicate the how this metric is doing"""
        return STAT_OK

    @property
    def last_updated(self):
        """Indicate the last time this metric was updated.
        
        Should return a datetime instances or None if not updated
        """
        return None

    @property
    def duration(self):
        """Returns a value indicating how long this metric has been under the current status value
        
        Return value is a datetime.timedelta instance
        """
        return datetime.timedelta(secs=0)

    @property
    def value(self):
        """Provide the actual value for this metric for display"""
        return None
    
    def add_to_loop(self, io_loop=None):
        """Do whatever is necessary to set this metric watcher up to actually collect data
        
        The io_loop is the tornado IOLoop instance, if None it will use the standard io loop global.
        """
        pass


class CommandMetricWatcher(MetricWatcher):
    """Metric watcher that executes a command periodically
    
    All this base class does is monitor the return value but sub-classes can easily extend it to do something with
    the commands output.
    """

    def __init__(self, *args, **kwargs):
        self._command = kwargs.pop('command', None)
        self._interval = kwargs.pop('interval', DEFAULT_INTERVAL)
        
        super(CommandMetricWatcher, self).__init__(*args, **kwargs)
        self._last_updated = None
        self._returncode = None
        self._status_start = None
        self._status = None
        
        self.set_status(STAT_OK)

    @property
    def command(self):
        return self._command

    @property
    def last_updated(self):
        return self._last_updated
    
    @property
    def status(self):
        return self._status

    @property
    def value(self):
        return self._returncode

    @property
    def duration(self):
        if self._status_start is None:
            return datetime.timedelta(0)
        else:
            return datetime.datetime.now() - self._status_start

    def set_updated(self):
        self._last_updated = datetime.datetime.now()

    def set_status(self, status):
        if self._status != status:
            self._status = status
            self._status_start = datetime.datetime.now()

    def handle_output(self, output):
        pass

    def handle_exit(self, returncode):
        self.set_updated()
        if returncode == 0:
            self.set_status(STAT_OK)
        else:
            self.set_status(STAT_CRITICAL)

        self._returncode = returncode

    def add_to_loop(self, io_loop=None):
        running = False
        def handle_interval():
            if running:
                log.warning("Interval while process is still running")
                return

            checker = subprocess.Popen(self.command, shell=True, stdout=subprocess.PIPE)
            log.debug("Started process %d : %s", checker.pid, self.command)
            def handle_events(fd, events):
                if events & io_loop.ERROR:
                    io_loop.remove_handler(checker.stdout.fileno())
                    if checker.poll() is None:
                        log.warning("fileno error (%d) but process hasn't exited ?", checker.stdout.fileno())
                        os.kill(checker.pid, signal.SIGTERM)
                        # This is dangerous since it can hang. But only in the case of a process that doesn't 
                        # want to exit for whatever reason.
                        checker.wait()

                    self.handle_exit(checker.returncode)

                if events & io_loop.READ:
                    output = checker.stdout.read()
                    self.handle_output(output)

                return

            io_loop.add_handler(checker.stdout.fileno(), handle_events, io_loop.READ)

        tornado.ioloop.PeriodicCallback(handle_interval, self._interval, io_loop=io_loop).start()


class PageGETMetricWatcher(CommandMetricWatcher):
    CURL_COMMAND = "curl -w \"%%{time_connect} %%{time_starttransfer} %%{time_total} (%%{http_code})\" -s -o /dev/null %(url)s"
    SSH_COMMAND = "ssh %(host)s \"%(command)s\""

    def __init__(self, *args, **kwargs):
        self._url = kwargs.pop('url', None)
        self._ssh_host = kwargs.pop('ssh_host', None)
        self._thresholds = kwargs.pop('thresholds', None)
        self._value = None
        
        super(PageGETMetricWatcher, self).__init__(*args, **kwargs)
    
    @property
    def command(self):
        out_cmd = self.CURL_COMMAND % {'url': self._url}

        if self._ssh_host:
            out_cmd = self.SSH_COMMAND % {'hostname': self._ssh_host, 'command': pipes.quote(out_cmd)}

        return out_cmd

    def handle_output(self, output):
        super(PageGETMetricWatcher, self).handle_output(output)

        self._output = output

        values = self._output.split()
        if len(values) != 4:
            self.set_status(STAT_CRITICAL)
            return
        
        connect_time, first_byte_time, total_time, status = values
        self._value = total_time = float(total_time)

        if status != '(200)':
            self.set_status(STAT_CRITICAL)
            return
        if self._thresholds is None:
            return
            
        min_val, warn_val, crit_val = self._thresholds
        if total_time <= min_val:
            self.set_status(STAT_WARNING)
            return

        if total_time >= crit_val:
            self.set_status(STAT_CRITICAL)
            return

        if total_time >= warn_val:
            self.set_status(STAT_WARNING)
            return

        self.set_status(STAT_OK)

    @property
    def value(self):
        if self._value is None:
            return "unknown"
        else:
            return "%.4f" % self._value


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        metric_watchers = getattr(self.application, "metric_watchers", list)
        for watcher in metric_watchers:
            self.write("%s: %s (%s for %s)<br />" % (watcher.name, watcher.value, watcher.status, format_timedelta(watcher.duration)))
