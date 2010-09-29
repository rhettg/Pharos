import os.path
import datetime

import pystache

class Dashboard(pystache.View):
    template_path = os.path.dirname(__file__)
    def generated_when(self):
        return datetime.datetime.now().strftime("%X %x")
    
