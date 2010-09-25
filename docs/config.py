import pharos

metric_watchers = [
    pharos.CommandMetricWatcher(name="Is True?", command="true"),
    pharos.CommandMetricWatcher(name="Is False?", command="false"),
    pharos.PageGETMetricWatcher(name="Is Google Up", url="http://www.google.com/", thresholds=(0.001, 0.100, 1.0)),
]
