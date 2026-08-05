import sys
import os

project_home = '/home/YOUR_USERNAME/safety_platform'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ['PYTHONANYWHERE'] = '1'

from app import app as application
