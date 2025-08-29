import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_transport.settings')
import django
django.setup()
from scripts.simulate_pickup import *
print('simulate run complete')
