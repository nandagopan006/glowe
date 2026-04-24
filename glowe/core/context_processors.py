from django.conf import settings
from django.templatetags.static import static
from product.models import Category

def global_settings(request):

    return {
        'logo_url': static('core/images/logo.png'),
        'site_name': getattr(settings, 'SITE_NAME', 'Glowé'),
        'categories': Category.objects.filter(is_deleted=False).order_by('name')
    }
