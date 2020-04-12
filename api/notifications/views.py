from django.urls import reverse
from django.views.generic import UpdateView, TemplateView
from django.http import HttpResponseRedirect
from django.conf import settings
from .models import Notifier


class SettingsView(UpdateView):
    model = Notifier
    template_name = 'settings.html'
    fields = (
        'email_follow',
        'email_transaction',
        'email_comment',
        'email_deposit',
        'email_like',
        'email_feed',
    )

    def get(self, *args, **kwargs):
        notifier = Notifier.objects.get(pk=kwargs['pk'])
        if not notifier.check_link_token(kwargs['token']):
            return HttpResponseRedirect(settings.REDIRECT_URL_NOTIFICATIONS)

        return super().post(*args, **kwargs)

    def post(self, *args, **kwargs):
        notifier = Notifier.objects.get(pk=kwargs['pk'])
        if not notifier.check_link_token(kwargs['token']):
            return HttpResponseRedirect(settings.REDIRECT_URL_NOTIFICATIONS)

        return super().post(*args, **kwargs)

    def get_success_url(self):
        return reverse('settings_success')


class SettingsSuccess(TemplateView):
    template_name = 'settings_success.html'


class UnsubscribeView(UpdateView):
    model = Notifier
    template_name = 'unsubscribe.html'
    fields = ()

    def get(self, *args, **kwargs):
        notifier = Notifier.objects.get(pk=kwargs['pk'])
        if not notifier.check_link_token(kwargs['token']):
            return HttpResponseRedirect(settings.REDIRECT_URL_NOTIFICATIONS)

        return super().post(*args, **kwargs)

    def post(self, *args, **kwargs):
        notifier = Notifier.objects.get(pk=kwargs['pk'])
        if not notifier.check_link_token(kwargs['token']):
            return HttpResponseRedirect(settings.REDIRECT_URL_NOTIFICATIONS)

        for field in SettingsView.fields:
            if type(getattr(notifier, field)) == bool:
                setattr(notifier, field, False)
            elif getattr(
                    notifier,
                    field,
            ) in [x[0] for x in Notifier.FREQUENCY]:
                setattr(notifier, field, Notifier.NEVER)
        notifier.save()
        return super().post(*args, **kwargs)

    def get_success_url(self):
        return reverse('unsubscribe_success')


class UnsubscribeSuccess(TemplateView):
    template_name = 'unsubscribe_success.html'
