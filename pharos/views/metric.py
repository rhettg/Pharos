import os.path
import pystache

class Metric(pystache.View):
    template_path = os.path.dirname(__file__)
