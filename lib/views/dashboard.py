import datetime

import pystache

class Dashboard(pystache.View):
    template_path = "lib/views"
    def generated_when(self):
        return datetime.datetime.now().strftime("%X %x")
    