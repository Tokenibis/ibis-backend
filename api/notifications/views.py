import ibis.models as models
import ibis.schema

from graphql_relay.node.node import from_global_id
from django.urls import reverse
from django.views import View
from django.views.generic import UpdateView, TemplateView
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from api.utils import get_submodel
from .models import Notifier, DonationMessage


class SettingsView(UpdateView):
    model = Notifier
    template_name = 'settings.html'
    fields = (
        'email_message',
        'email_follow',
        'email_reward',
        'email_comment',
        'email_mention',
        'email_deposit',
    )

    def get(self, *args, **kwargs):
        notifier = Notifier.objects.get(pk=kwargs['pk'])
        if not notifier.check_link_token(kwargs['token']):
            return HttpResponseRedirect(settings.REDIRECT_URL_NOTIFICATIONS)
        if self.request.path.split(
                '/'
        )[-4] != 'organization_settings' and models.Organization.objects.filter(
                id=notifier.user.id).exists():
            return HttpResponseRedirect(
                reverse('organization_settings', kwargs=kwargs))

        return super().post(*args, **kwargs)

    def post(self, *args, **kwargs):
        notifier = Notifier.objects.get(pk=kwargs['pk'])
        if not notifier.check_link_token(kwargs['token']):
            return HttpResponseRedirect(settings.REDIRECT_URL_NOTIFICATIONS)

        return super().post(*args, **kwargs)

    def get_success_url(self):
        return reverse('settings_success')


class OrganizationSettingsView(SettingsView):
    fields = (
        'email_message',
        'email_follow',
        'email_donation',
        'email_comment',
        'email_mention',
        'email_withdrawal',
    )


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


class DonationMessageView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse(
            DonationMessage.objects.order_by("?").first().description.format(
                organization=kwargs['name']))


class AppLinkView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse(
            settings.APP_LINK_RESOLVER('{}:{}'.format(
                get_submodel(
                    getattr(
                        ibis.schema,
                        from_global_id(kwargs['gid'])[0],
                    )._meta.model.objects.get(
                        id=from_global_id(kwargs['gid'])[1])).__name__,
                kwargs['gid'],
            )))
