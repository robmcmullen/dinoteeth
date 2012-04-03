import os

def init_orm(pathname):
    from django.conf import settings

    kw = {
        'DATABASES': {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': pathname,
                }
            },
        'INSTALLED_APPS': (
            'dinoteeth.standalone',
            ),
    }

    settings.configure(**kw)
    
    if not os.path.exists(pathname) or os.path.getsize(pathname) == 0:
        from django.core.management import call_command
        call_command('syncdb')
