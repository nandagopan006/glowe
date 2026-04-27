import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'glowe.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

def update_site_config():
    site = Site.objects.get(id=1)
    site.domain = '127.0.0.1:8000'
    site.name = 'Glowé'
    site.save()
    print(f"Updated Site: {site.domain}")

    # Ensure the Google app is linked to this site
    app = SocialApp.objects.filter(provider='google').first()
    if app:
        app.sites.add(site)
        print(f"Linked '{app.name}' to site {site.domain}")

if __name__ == "__main__":
    update_site_config()
