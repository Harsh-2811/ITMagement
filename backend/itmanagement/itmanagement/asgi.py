import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path, include

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'itmanagement.settings')
django.setup()

application = ProtocolTypeRouter({
    "http": URLRouter([
        path("events/", include("django_eventstream.urls")),
        path("", get_asgi_application()),
    ]),
})
