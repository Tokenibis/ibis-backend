from django.apps import AppConfig


class IbisConfig(AppConfig):
    name = 'ibis'

    def ready(self):
        import ibis.signals
