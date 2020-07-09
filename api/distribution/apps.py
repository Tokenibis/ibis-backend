from django.apps import AppConfig


class DistributionConfig(AppConfig):
    name = 'distribution'

    def ready(self):
        import distribution.signals
