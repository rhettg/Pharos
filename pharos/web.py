import time
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

def build_watcher_set_context(watcher_set):
    context = {
        'name': watcher_set.name,
        'metric_watchers': list(),
    }
    for watcher in watcher_set.watchers:
        context['metric_watchers'].append(build_watcher_context(watcher))
    
    return context

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        metric_watcher_sets = getattr(self.application, "metric_watcher_sets", list)
        context = {
            'metric_watcher_sets': list(),
            'page_tag': getattr(self.application, "page_tag", "Keeps watch...")
        }

        for watcher_set in metric_watcher_sets:
            context['metric_watcher_sets'].append(build_watcher_set_context(watcher_set))

        self.write(dashboard.Dashboard(context=context).render())


class PollJSONHandler(tornado.web.RequestHandler):
    def get(self):
        metric_watcher_sets = getattr(self.application, "metric_watcher_sets", list())
        context = {
            'metric_watchers': list()
        }

        for watcher_set in metric_watcher_sets:
            for watcher in watcher_set.watchers:
                context['metric_watchers'].append(build_watcher_context(watcher))

        # Testing data
        # context['metric_watchers'].append(dict(id="home_com_slw", name="home.com from slw", status_ok=True, value="3.503", duration=format_timedelta(datetime.timedelta(seconds=300)), detail="some stuff"))
        # context['metric_watchers'].append(dict(id="bizdetails_com_slw", name="bizdetails.com from slw", status_ok=True, value="10.503", duration=format_timedelta(datetime.timedelta(seconds=80)), detail="some other stuff"))
        self.write(context)
    
