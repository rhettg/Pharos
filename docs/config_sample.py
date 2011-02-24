import pharos

# Optional page title, defaults to 'Pharos'
page_tag = "Watching so you don't have to"

metric_watcher_sets = [
	pharos.WatcherSet('Watch Set 1', 
					  [
						pharos.CommandMetricWatcher(name="Is True?", command="true"),
					    pharos.CommandMetricWatcher(name="Is False?", command="false"),
					    pharos.PageGETMetricWatcher(name="Is Google Up", url="http://www.google.com/", thresholds=(0.001, 0.100, 1.0)),
				
	]),
	pharos.WatcherSet('Watch Set 2', 
					  [
						pharos.CommandMetricWatcher(name="Also True?", command="true"),
					    pharos.CommandMetricWatcher(name="Also False?", command="false"),
					    pharos.PageGETMetricWatcher(name="Is Apple Up", url="http://www.apple.com/", thresholds=(0.001, 0.100, 1.0)),
				
	])

]
