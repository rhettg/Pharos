import datetime

from testify import *

import pharos

class FormatTimeDetltaTestCase(TestCase):
    def test_short(self):
        assert_equal(pharos.format_timedelta(datetime.timedelta(seconds=1)), "a moment")
    def test_really_long(self):
        assert_equal(pharos.format_timedelta(datetime.timedelta(seconds=10*60*60*24)), "10 days")
    def test_a_minute(self):
        assert_equal(pharos.format_timedelta(datetime.timedelta(seconds=65)), "1 minute")
    def test_mid_minutes(self):
        assert_equal(pharos.format_timedelta(datetime.timedelta(seconds=60*5+30)), "5 minutes")

    def test_an_hour(self):
        assert_equal(pharos.format_timedelta(datetime.timedelta(seconds=3600+65)), "1 hour")
    def test_mid_hours(self):
        assert_equal(pharos.format_timedelta(datetime.timedelta(seconds=3600*2+100)), "2 hours")
    def test_a_day(self):
        assert_equal(pharos.format_timedelta(datetime.timedelta(days=1)), "1 day")


if __name__ == '__main__':
    run()