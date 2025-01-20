import os
import sys	

sys.path.insert(0, '/var/www/html/webdc3/wsgi/')

import webinterface

application = webinterface.application
