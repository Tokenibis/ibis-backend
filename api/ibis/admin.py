import os
import ibis.models as models

from django.db import transaction
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime
from django.utils.dateparse import parse_datetime
from django.http import HttpResponseRedirect
from django.urls import path
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm
from graphql_relay.node.node import to_global_id


class UserAdminChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = models.User


class OrganizationAdminChangeForm(UserChangeForm):
    avatar_upload = forms.FileField(required=False)
    banner_upload = forms.FileField(required=False)

    def save(self, commit=True):
        avatar_upload = self.cleaned_data.get('avatar_upload', None)
        banner_upload = self.cleaned_data.get('banner_upload', None)

        if avatar_upload:
            self.instance.avatar = models.store_image(
                avatar_upload,
                os.path.join(
                    'avatar',
                    to_global_id('UserNode', self.instance.id),
                ),
            )

        if banner_upload:
            self.instance.banner = models.store_image(
                banner_upload,
                os.path.join(
                    'banner',
                    to_global_id('UserNode', self.instance.id),
                ),
            )

        return super().save(commit=commit)


@admin.register(models.Organization)
class OrganizationAdmin(UserAdmin):
    form = OrganizationAdminChangeForm
    ordering = ['-date_joined']
    fieldsets = ((
        None,
        {
            'fields': (
                'username',
                'first_name',
                'email',
                'description',
                'link',
                'password',
                'is_active',
                'category',
                'score',
                'avatar_upload',
                'banner_upload',
                'balance_str',
                'fundraised_str',
            )
        },
    ), )

    readonly_fields = ('balance_str', 'fundraised_str')
    list_display = ('username', 'name', 'balance_str', 'fundraised_str')

    def name(self, obj):
        return str(obj)

    def balance_str(self, obj):
        return '${:,.2f}'.format(obj.balance() / 100)

    def fundraised_str(self, obj):
        return '${:,.2f}'.format(obj.fundraised() / 100)


@admin.register(models.Person)
class PersonAdmin(UserAdmin):
    form = UserAdminChangeForm
    ordering = ['-date_joined']
    fieldsets = ((
        None,
        {
            'fields': (
                'username',
                'first_name',
                'last_name',
                'email',
                'description',
                'password',
                'is_active',
                'score',
                'avatar',
                'balance_str',
                'donated_str',
                'referral',
                'verified',
            )
        },
    ), )

    readonly_fields = ('balance_str', 'donated_str')
    list_display = ('username', 'name', 'balance_str', 'donated_str')

    def name(self, obj):
        return str(obj)

    def balance_str(self, obj):
        return '${:,.2f}'.format(obj.balance() / 100)

    def donated_str(self, obj):
        return '${:,.2f}'.format(obj.donated() / 100)


@admin.register(models.Bot)
class BotAdmin(UserAdmin):
    form = UserAdminChangeForm
    ordering = ['-date_joined']
    fieldsets = ((
        None,
        {
            'fields': (
                'username',
                'first_name',
                'email',
                'description',
                'password',
                'is_active',
                'score',
                'avatar',
                'balance_str',
                'rewarded_str',
            )
        },
    ), )

    readonly_fields = ('balance_str', 'rewarded_str')
    list_display = ('username', 'name', 'balance_str', 'rewarded_str')

    def name(self, obj):
        return str(obj)

    def balance_str(self, obj):
        return '${:,.2f}'.format(obj.balance() / 100)

    def rewarded_str(self, obj):
        return '${:,.2f}'.format(obj.rewarded() / 100)


class GrantDonationInline(admin.TabularInline):
    model = models.GrantDonation
    extra = 0
    raw_id_fields = ('grant', 'donation')


@admin.register(models.Grant)
class GrantAdmin(admin.ModelAdmin):
    raw_id_fields = ('funded', 'user')
    ordering = ('-created', )
    # inlines = (GrantDonationInline, )


@admin.register(models.Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    change_list_template = "withdrawal_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('settle-balances/', self.settle_balances),
        ]
        return my_urls + urls

    def get_balances(self, time):
        return sorted(
            [(x, x.balance(time=time))
             for x in models.Organization.objects.all()
             if x.balance(time=time) > settings.SETTLE_BALANCE_MIN
             and x.is_active and x.username != settings.IBIS_USERNAME_ROOT],
            key=lambda x: str(x[0]),
        )

    def get_changelist(self, request, *args, **kwargs):
        time = localtime()
        request.session['settle_balance_time'] = str(time)
        balances = self.get_balances(time)
        message = 'Outstanding Balances<br/><br/>{}{}Total: ${:,.2f}'.format(
            '<br/>'.join('{}: ${:,.2f}'.format(org, bal / 100)
                         for org, bal in balances),
            '<br/><br/>' if balances else '',
            sum(bal for _, bal in balances) / 100,
        )

        self.message_user(request, mark_safe(message))
        return super().get_changelist(request, *args, **kwargs)

    def settle_balances(self, request):
        with transaction.atomic():
            for org, bal in self.get_balances(
                    parse_datetime(request.session['settle_balance_time'])):
                models.Withdrawal.objects.create(
                    user=org,
                    amount=bal,
                    description='admin',
                    category=models.ExchangeCategory.objects.get(
                        title='check'),
                )
        self.message_user(request, 'Success. All balances have been settled')
        return HttpResponseRedirect('../')


admin.site.register(models.OrganizationCategory)
admin.site.register(models.ExchangeCategory)
admin.site.register(models.News)
admin.site.register(models.Event)
admin.site.register(models.Donation)
admin.site.register(models.Post)
admin.site.register(models.Reward)
admin.site.register(models.Activity)
admin.site.register(models.Comment)
admin.site.register(models.Deposit)
admin.site.register(models.Entry)
admin.site.register(models.Channel)
admin.site.register(models.MessageDirect)
admin.site.register(models.MessageChannel)
