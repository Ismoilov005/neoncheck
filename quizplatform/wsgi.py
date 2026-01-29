import os
import sys

# Loyiha yo'li
path = '/home/neoncheck/neoncheck'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'quizplatform.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()