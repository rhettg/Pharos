import pipes

import pharos

metric_watchers = [
    pharos.CommandMetricWatcher(name="Is True?", command="true"),
    pharos.PageGETMetricWatcher(name="home.ie from localhost", url="http://www.yelp.ie/", thresholds=(0.001, 0.800, 3.0))
]
