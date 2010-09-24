import pharos

class PageStats(pharos.StatWatcher):
    interval = 3000
    id = "batch2.curl.yelpie.home"
    name = "home from batch2"
    command = "ssh batch2 \"curl -w \\\"%{time_connect} %{time_starttransfer} %{time_total} (%{http_code})\\\" -s -o /dev/null http://www.yelp.ie/\""
    threasholds = (0.001, 1.0, 5.0)

    def __init__(self):
        self._value = None
        super(PageStats, self).__init__()

    def handle_output(self, output):
        super(PageStats, self).handle_output(output)

        self._output = output
        values = self._output.split()
        if len(values) != 4:
           self._status = pharos.STAT_CRITICAL 
           return
        
        connect_time, first_byte_time, total_time, status = values
        self._value = total_time = float(total_time)

        if status != '(200)':
            self._status = pharos.STAT_CRITICAL
            return

        min_val, warn_val, crit_val = self.threasholds
        if total_time <= min_val:
            self._status = pharos.STAT_WARNING
            return

        if total_time >= crit_val:
            self._status = pharos.STAT_CRITICAL
            return

        if total_time >= warn_val:
            self._status = pharos.STAT_WARNING
            return

        self._status = pharos.STAT_OK

    @property
    def value(self):
        if self._value is None:
            return "unknown"
        else:
            return "%.4f" % self._value


watch_stats = [
    PageStats(),
]
