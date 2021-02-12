from django.conf import settings
from django.shortcuts import render
from django.views.generic import FormView, TemplateView
from django.http import HttpResponseRedirect
from django.urls import reverse
from gifts.models import Gift, GiftType
from gifts.forms import GiftForm


class ChooseView(FormView):
    template_name = 'gift_choose.html'
    form_class = GiftForm
    model = Gift

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, *args, **kwargs):
        gift = Gift.objects.get(pk=self.kwargs['pk'])

        if gift.withdrawal or Gift.objects.filter(
                user=gift.user, created__gt=gift.created).exists():
            return HttpResponseRedirect(reverse('gift_error'))

        kwargs = super().get_form_kwargs()
        kwargs['gift'] = gift
        return kwargs

    def form_valid(self, form):
        gift = Gift.objects.get(pk=self.kwargs['pk'])
        choice_id = int(form.cleaned_data['choice'])
        gift.send_gift(
            GiftType.objects.get(id=choice_id) if choice_id else None,
            form.cleaned_data['address'],
            form.cleaned_data['suggestion'],
        )
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        try:
            gift = Gift.objects.get(pk=self.kwargs['pk'])
        except Exception:
            return HttpResponseRedirect(reverse('gift_error'))

        if request.user.id != gift.user.id:
            return HttpResponseRedirect(reverse('gift_error'))

        if gift.withdrawal or Gift.objects.filter(
                user=gift.user, created__gt=gift.created).exists():
            return HttpResponseRedirect(reverse('gift_error'))

        return super().post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        gift = Gift.objects.get(pk=self.kwargs['pk'])
        if request.user.id != gift.user.id:
            return HttpResponseRedirect(reverse('gift_error'))
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        # if referrer, go to referrer page
        # else just go tokenibis home page
        return reverse('gift_success')


class SuccessView(TemplateView):
    template_name = 'gift_success.html'
    context = {
        'return_link': settings.APP_LINK_RESOLVER(),
    }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.context)


class ErrorView(TemplateView):
    template_name = 'gift_error.html'
    context = {
        'return_link': settings.APP_LINK_RESOLVER(),
    }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.context)
