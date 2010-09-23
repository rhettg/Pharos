import pharos

class PageStats(pharos.StatWatcher):
    interval = 3000
    command = "ssh batch2 \"curl -w \\\"%{time_connect} %{time_starttransfer} %{time_total} (%{http_code})\\\" -s -o /dev/null http://www.yelp.ie/\""

    def __init__(self):
        self._value = None
        super(PageStats, self).__init__()

    def handle_output(self, output):
        self._value = output

    @property
    def value(self):
        return str(self._value)


watch_stats = [
    PageStats(),
]