Pharos
=======

Pharos is a tool for real time monitoring. It attempts to fill the hole that exists between traditional metric reporting
systems (ganglia, munin, etc) and notification systems (nagios)

Pharos doesn't attempt to track how a metric changes over time. There are no graphs. It will not send a notification to your pager.

Pharos is a dashboard that put up so you can watch, in near real time, how your systems are performing.

Example Usage
---------------

![Example Dashboard](http://github.com/rhettg/Pharos/raw/master/docs/dashboard.png)

Let's say you run a web site. Let's call that website google.com

You already have ganglia tracking all your systems. Nice graphs of CPU load averages over the last 10 years. You know it's time
to buy another pallet of servers because your graphs pass certain thresholds. You already get notified via nagios to your phone
when the site goes down because your MySQL server just fell over.

However, you still get complaints from your CEO every few days when he complains that the page loaded kinda slow momentarily.

Your graphs look fine. On average, your users are seeing 100ms response times. Even the 99th percentile is only 150ms.
Sure maybe a little noisy but nothing seems that wrong. No pages went off.

Enter Pharos.

Pharos can act like a normal user is the simplest way. You set up Pharos to hit your site every second and see how long it takes.

What you might see with Pharos is the whole board is green most of the day. But every once in a while it flickers yellow, then red.
Then back to green. 

Simple. Effective. But of course just part of your overall analytics solution.

Pharos is pretty flexible with what kind of thing it reports on. It comes batteries included with a way to execute `curl` and
collect some nice stats on downloading your page. You can also have just execute any regular command and complain if it returns
a bad exit status.

So put Pharos up on your dashboards in the office and get a feel for how your infrastructure is working from a new perspective.

Installation
--------------

Pharos is a python application. It comes complete with standard python setup.py 

Pharos has requirements on some other python packages that are probably not standard:

* tornado (async/event based web framework)
* pystache (template library)

In addition, the current version of pystache has a [bug](http://github.com/defunkt/pystache/issues#issue/13). 
I have a fix. So you should get my version of pystache until my fix is accepted.

The easiest way to get started is to use excellent python packaging tools 'virtualenv' and 'pip':

    virtualenv pharos_env
    pip install -E pharos_env git+git://github.com/rhettg/Pharos.git#egg=pharos
    pip install -E pharos_env git+git://github.com/rhettg/pystache.git#egg=pystache
    pip install -E pharos_env tornado

Then you should be able to run the pharos daemon out of the box

    cd pharos_env
    bin/pharosd

If you run pharos outside of virtualenv, you're on your own for tracking down the necessary paths for pharosd. I don't
have a good plan for that yet. Debian packaging and whatnot would probably a good idea at some point.

Configuration
---------------

Configuration is one via a python-based configuration file. This makes extending pharos very easy because if the provided
'MetricWatcher' classes don't do it for you, you can just sub-class them in your configuration file and do whatever you
want.

The example configuration looks like this:

    import pharos

    metric_watchers = [
        pharos.CommandMetricWatcher(name="Is True?", command="true"),
        pharos.CommandMetricWatcher(name="Is False?", command="false"),
        pharos.PageGETMetricWatcher(name="Is Google Up", url="http://www.google.com/", thresholds=(0.001, 0.100, 1.0)),
    ]

A 'CommandMetricWatcher' simply executes a command. If it returns successfully you're good, if it fails it's marked as Critical.

A PageGetMetricWatcher executes 'curl' with some fancy options that give you some metrics on how long it took to download
the page. You can provide threshold values to indicate what a bad response would be.

There are a few options you can tune. Of interest might be `ssh_host` and `interval`. See
[watcher.py](http://github.com/rhettg/Pharos/blob/master/pharos/watcher.py) for more details.

