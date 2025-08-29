import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','smart_transport.settings')
import django
django.setup()
from django.urls import reverse
print('reverse logout ->', reverse('logout'))
