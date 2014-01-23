import os
import sys	

sys.path.insert(0, '/var/www/webinterface/wsgi/')

import webinterface

application = webinterface.application
