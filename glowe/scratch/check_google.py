import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'glowe.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

def check_google_config():
    apps = SocialApp.objects.filter(provider='google')
    if not apps.exists():
        print("ERROR: No SocialApp configured for 'google' in the database.")
        return

    for app in apps:
        print(f"App: {app.name}")
        print(f"Provider: {app.provider}")
        print(f"Client ID: {app.client_id[:10]}...")
        print(f"Secret: {app.secret[:5]}...")
        print(f"Sites: {[site.domain for site in app.sites.all()]}")
        
    sites = Site.objects.all()
    print(f"Available Sites: {[site.domain for site in sites]}")
    print(f"Current SITE_ID: {django.conf.settings.SITE_ID}")

if __name__ == "__main__":
    check_google_config()
