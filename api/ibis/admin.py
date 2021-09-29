import os

from django import forms
from django.contrib import admin
from graphql_relay.node.node import to_global_id

import ibis.models as models
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm


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
        return '${:.2f}'.format(obj.balance() / 100)

    def fundraised_str(self, obj):
        return '${:.2f}'.format(obj.fundraised() / 100)


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
        return '${:.2f}'.format(obj.balance() / 100)

    def donated_str(self, obj):
        return '${:.2f}'.format(obj.donated() / 100)


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
        return '${:.2f}'.format(obj.balance() / 100)

    def rewarded_str(self, obj):
        return '${:.2f}'.format(obj.rewarded() / 100)


class InvestmentDonationInline(admin.TabularInline):
    model = models.InvestmentDonation
    extra = 0


@admin.register(models.Investment)
class InvestmentAdmin(admin.ModelAdmin):
    raw_id_fields = ('funded', )
    inlines = (InvestmentDonationInline, )


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
admin.site.register(models.Withdrawal)
admin.site.register(models.Entry)
admin.site.register(models.Channel)
admin.site.register(models.MessageDirect)
admin.site.register(models.MessageChannel)
