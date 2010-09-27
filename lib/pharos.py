import os
import sys
import re
import errno
import signal
import socket
import subprocess
import datetime
import logging
import pipes

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.httpclient
import pystache

import views.dashboard
import views.metric

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
        self._callbacks = []

    @property
    def id(self):
        """Build an id for this metric
        
        We'll build an id based on the name by stripping out whitespace and non-alphanumeric characters
        """
        id_str = re.sub(r'[\s]', '_', self.name.lower())
        id_str = re.sub(r'[^\w]', '', id_str)
        return id_str
        

    @property
    def status(self):
        """Returns one of our STAT_* constants to indicate the how this metric is doing"""
        raise 'whaaa'
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
    
    @property
    def detail(self):
        """Provide more details for drilldown in this stat"""
        return None
    
    def add_update_callback(self, callback):
        """Calls function 'callback' on the next update to this metric"""
        self._callbacks.append(callback)
    
    def _callback(self):
        while self._callbacks:
            try:
                self._callbacks.pop()()
            except Exception, e:
                log.exception("Error calling callback")
    
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
        self._metric_checker = None
        
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
        log.debug("Setting status for %s : %s", self.name, status)
        self._callback()
        if self._status != status:
            self._status = status
            self._status_start = datetime.datetime.now()

    def _handle_output(self, output):
        pass

    def _handle_returncode(self, returncode):
        self._returncode = returncode

        if returncode == 0:
            self.set_status(STAT_OK)
        else:
            self.set_status(STAT_CRITICAL)

        self.set_updated()

    def handle_exit(self):
        assert self._metric_checker, "we should have an open checker, or you shouldn't have called me."

        returncode = self._metric_checker.returncode
        assert returncode is not None, "Process should have exited, or else why are we here"

        log.debug("Process %d exited with value %d", self._metric_checker.pid, returncode)

        self._metric_checker = None
        self._handle_returncode(returncode)

    def add_to_loop(self, io_loop=None):

        # There is some amount of complexity in here that is worth explaining. What we're going to setup here
        # is a periodic callback in our tornado io loop that will start a process, monitor for output and process
        # the process's exit. It makes use of closures because we need internal state, but the callbacks don't have
        # the luxury of arguments. 
        #
        # There should be only one process running at once. If it hangs or does something stupid we're not going to start
        # another, but we will complain in the logs.

        def handle_interval():
            """Callback for our PeriodicCallback interval. 
            
            The only important *state* in this closure is 'self', which wouldn't be available normally.
            """
            if self._metric_checker is not None:
                if self._metric_checker.poll() is not None:
                    self.handle_exit()
                else:
                    log.warning("Interval while process is still running (pid %d)", self._metric_checker.pid)
                    return
                
            checker = self._metric_checker = subprocess.Popen(self.command, shell=True, stdout=subprocess.PIPE)
            log.debug("Started process %d : %s", checker.pid, self.command)

            def check_for_exit():
                if checker.poll() is not None:
                    io_loop.remove_handler(checker.stdout.fileno())
                    self.handle_exit()

            # Mmm.. another closure. This one is for our event processing
            def handle_events(fd, events):
                # We need to make sure we still care about the output from this checker
                if self._metric_checker is None or fd != self._metric_checker.stdout.fileno():
                    log.warning("IO handler was still active for fd %d", fd)
                    io_loop.remove_handler(fd)
                    return

                assert self._metric_checker

                if events & io_loop.READ:
                    output = checker.stdout.read()
                    if len(output) == 0:
                        # On OSX this seems to be what happens rather than receiving an error....strange
                        #log.warning("Got no output from %d ?", fd)
                        check_for_exit()
                    else:
                        self._handle_output(output)

                if events & io_loop.ERROR:
                    # We're definetly over this fd, but the process may not have actually exited.
                    # So we'll remove it from the io loop, and if exit was delayed it will get cleaned up
                    # on the next interval. In practice this should rarely happen.
                    io_loop.remove_handler(fd)
                    check_for_exit()
                    
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
        self._output = None
        
        super(PageGETMetricWatcher, self).__init__(*args, **kwargs)
    
    @property
    def command(self):
        out_cmd = self.CURL_COMMAND % {'url': self._url}

        if self._ssh_host:
            out_cmd = self.SSH_COMMAND % {'hostname': self._ssh_host, 'command': pipes.quote(out_cmd)}

        return out_cmd

    def _handle_output(self, output):
        log.debug("Received %r", output)
        super(PageGETMetricWatcher, self)._handle_output(output)

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
            raise Exception('no thresholds')
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

    def _handle_returncode(self, returncode):
        if returncode != 0:
            self.set_status(STAT_CRITICAL)
            self.set_updated()

        self._returncode = returncode
        
    @property
    def value(self):
        if self._value is None:
            return "unknown"
        else:
            return "%.4f" % self._value

    @property
    def detail(self):
        return self._output

def build_watcher_context(watcher):
    context = {
        "id": watcher.id,
        "name": watcher.name,
        "status_ok": watcher.status == STAT_OK,
        "status_warning": watcher.status == STAT_WARNING,
        "status_critical": watcher.status == STAT_CRITICAL,
        "value": watcher.value,
        "detail": watcher.detail,
        "duration": format_timedelta(watcher.duration)
    }
    
    return context

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        metric_watchers = getattr(self.application, "metric_watchers", list)
        context = {
            'metric_watchers': list()
        }

        for watcher in metric_watchers:
            context['metric_watchers'].append(build_watcher_context(watcher))

        # Testing data
        # context['metric_watchers'].append(dict(name="home.com from slw", status_warning=True, value="3.503", duration=format_timedelta(datetime.timedelta(seconds=2))))
        # context['metric_watchers'].append(dict(name="bizdetails.com from slw", status_critical=True, value="13.503", duration=format_timedelta(datetime.timedelta(seconds=80))))
        
        self.write(views.dashboard.Dashboard(context=context).render())

class PartialMetricHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, metric_id):
        metric_watchers = getattr(self.application, "metric_watchers", list)
        for watcher in metric_watchers:
            if watcher.id == metric_id:
                break
        else:
            self.send_error(status_code=404)
        
        # We found our watcher, which is all well and good, but now we're going to wait until the next
        # update before we actually return a response. That way the client can have a super fast polling interval and always
        # have the lastest data
        
        def complete():
            context = build_watcher_context(watcher)
            self.write(views.metric.Metric(context=context).render())
            self.finish()
        
        watcher.add_update_callback(complete)