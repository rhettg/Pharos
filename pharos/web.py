import re
import datetime
import logging

import tornado.web
import tornado.httpclient

from pharos.watcher import STAT_OK, STAT_WARNING, STAT_CRITICAL
from pharos.views import dashboard
from pharos.views import metric

log = logging.getLogger('pharos.web')

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
        
        self.write(dashboard.Dashboard(context=context).render())


class PollMetricHandler(tornado.web.RequestHandler):
    def get(self, metric_id):
        metric_watchers = getattr(self.application, "metric_watchers", list)
        for watcher in metric_watchers:
            if watcher.id == metric_id:
                break
        else:
            self.send_error(status_code=404)
        
        # At one point I had this as an async call. It was very cool. However
        # it causes the browser to *spin*, meaning it looks like it's always
        # loading something. I guess this is because the requests would take
        # one or more seconds and it thought it would be good to let you know
        # it's slow. Alas, this method isn't too bad either.

        context = build_watcher_context(watcher)
        self.write(metric.Metric(context=context).render())
        self.finish()
        
