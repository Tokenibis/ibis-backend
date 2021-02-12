import gifts.models
import ibis.models
from django.core import management
from django.conf import settings
from freezegun import freeze_time
from api.test.base import BaseTestCase, TEST_TIME
from django.utils.timezone import utc


class GiftTestCase(BaseTestCase):
    @freeze_time(TEST_TIME.astimezone(utc).date())
    def test_gifts(self):
        settings.GIFT_PROBABILITY_HOURLY = 1

        root_org = ibis.models.Organization.objects.get(
            username=settings.IBIS_USERNAME_ROOT)

        num_messages = ibis.models.Message.objects.count()
        num_gifts = gifts.models.Gift.objects.count()
        balance = root_org.balance()

        management.call_command('give')

        assert ibis.models.Message.objects.count() == num_messages + 1
        assert gifts.models.Gift.objects.count() == num_gifts + 1

        gift = gifts.models.Gift.objects.order_by('created').last()

        gift.send_gift(gift.choices.order_by('?').first(), '1234 Main St', 'None')

        assert gift.choice
        assert root_org.balance() == balance - settings.GIFT_AMOUNT
