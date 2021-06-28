import random
import ibis.models

from django.conf import settings
from django.urls import reverse
from django.db import models
from django.utils.timezone import localtime, timedelta
from model_utils.models import TimeStampedModel
from django.core.validators import MinLengthValidator

MESSAGE_TEMPLATE = '''Hi {name},

Congratulations! As recently active user, you've been randomly
selected for our latest community appreciation prize. Just fill out
this little [form]({link}) and we'll do the rest.

Sincerely,

The Token Ibis Team

---

_This is an automated message, but you're welcome to respond and a
human will get back to you eventually._
'''


def initiate_gift():
    if GiftType.objects.count() < settings.GIFT_CHOICE_MIN:
        print('Not enough gift choices')
        return

    if ibis.models.Organization.objects.get(
            username=settings.IBIS_USERNAME_ROOT).balance() < 0:
        print('Not enough funds to intiiate gift')
        return

    if not ibis.models.Donation.objects.filter(
            created__gte=localtime() -
            timedelta(settings.GIFT_HORIZON_DAYS)).exists():
        print('No recent donatoins')
        return

    user = random.choice(
        list(
            set(
                x.user for x in ibis.models.Donation.objects.filter(
                    created__gte=localtime() -
                    timedelta(days=settings.GIFT_HORIZON_DAYS)))))

    gift = Gift.objects.create(user=user)

    for x in GiftType.objects.order_by('?')[:settings.GIFT_CHOICE_NUMBER]:
        gift.choices.add(x)

    ibis.models.MessageDirect.objects.create(
        user=ibis.models.Organization.objects.get(
            username=settings.IBIS_USERNAME_ROOT),
        target=user,
        description=MESSAGE_TEMPLATE.format(
            name=user.first_name,
            link='{}/{}'.format(
                settings.API_ROOT_PATH,
                reverse('gift_choose', args=[gift.pk]),
            ),
        ),
    )


class GiftType(models.Model):
    title = models.TextField(unique=True, validators=[MinLengthValidator(1)])
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class Gift(TimeStampedModel):
    user = models.ForeignKey(
        ibis.models.Person,
        on_delete=models.CASCADE,
    )

    choices = models.ManyToManyField(
        GiftType,
        related_name='option_for',
    )

    choice = models.ForeignKey(
        GiftType,
        on_delete=models.CASCADE,
        null=True,  # interpret null as defer
    )

    withdrawal = models.ForeignKey(
        ibis.models.Withdrawal,
        on_delete=models.CASCADE,
        null=True,  # if null, then gift has not been processed yet
    )

    address = models.TextField(default='', blank=True)
    suggestion = models.TextField(default='', blank=True)
    processed = models.BooleanField(default=False)

    def get_amount(self):
        if self.withdrawal:
            return self.withdrawal.amount
        else:
            amount = settings.GIFT_AMOUNT
            for x in Gift.objects.filter(user=self.user).exclude(
                    id=self.id).order_by('-created'):
                if not x.withdrawal:
                    amount += settings.GIFT_AMOUNT
                else:
                    break
            return amount

    def send_gift(self, choice, address, suggestion):
        self.choice = choice
        self.address = address
        self.suggestion = suggestion

        if choice and not self.withdrawal:
            self.withdrawal = ibis.models.Withdrawal.objects.create(
                user=ibis.models.Organization.objects.get(
                    username=settings.IBIS_USERNAME_ROOT),
                amount=self.get_amount(),
                category=ibis.models.ExchangeCategory.objects.get(
                    title=settings.GIFT_EXCHANGE_CATEGORY),
            )

        self.save()
