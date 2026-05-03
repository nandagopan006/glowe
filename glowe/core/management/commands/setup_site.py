"""
Management command to create the required Site entry for django.contrib.sites
and configure allauth SocialApp for Google OAuth.
Run this after flush + loaddata to restore the site configuration.
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = "Setup the required Site entry for django.contrib.sites"

    def handle(self, *args, **options):
        # Update or create the default site with your domain
        site, created = Site.objects.update_or_create(
            id=1,
            defaults={
                "domain": "nandagopan.online",
                "name": "Glowé",
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✅ Site created: nandagopan.online"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Site updated: nandagopan.online"))
