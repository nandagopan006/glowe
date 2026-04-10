from django.conf import settings
from django.templatetags.static import static

def global_settings(request):
    """
    Global context processor to pass common variables to all templates.
    Avoids hardcoding paths in templates and makes global changes easy.
    """
    return {
        'logo_url': static('core/images/logo.png'),
        'site_name': getattr(settings, 'SITE_NAME', 'Glowé'),
    }
