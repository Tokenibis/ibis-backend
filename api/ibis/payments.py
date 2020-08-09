import logging
from django.conf import settings

from paypalcheckoutsdk.core import PayPalHttpClient
from paypalcheckoutsdk.core import SandboxEnvironment, LiveEnvironment
from paypalcheckoutsdk.orders import OrdersGetRequest
from braintreehttp.http_error import HttpError

logger = logging.getLogger(__name__)


class PayPalClient:
    def __init__(self):
        if settings.PAYPAL_USE_SANDBOX:
            environment = SandboxEnvironment(
                client_id=settings.PAYPAL_SANDBOX_CLIENT_ID,
                client_secret=settings.PAYPAL_SANDBOX_SECRET_KEY,
            )
        else:
            environment = LiveEnvironment(
                client_id=settings.PAYPAL_LIVE_CLIENT_ID,
                client_secret=settings.PAYPAL_LIVE_SECRET_KEY,
            )

        # Returns PayPal HTTP client instance with environment that
        # has access credentials context. Use this instance to invoke
        # PayPal APIs, provided the credentials have access.
        self.client = PayPalHttpClient(environment)

    def get_order(self, order_id):
        """Query the PayPal api for information about the order. Return the
        amount of the payment (in cents) upon success or 0 otherwise

        """

        try:
            request = OrdersGetRequest(order_id)
            response = self.client.execute(request)
        except HttpError as e:
            logger.error('HttpError while fetching PayPal order: {}'.format(e))
            return '', 0

        try:
            assert response.result.intent == 'CAPTURE', 'bad payment intent'
            assert response.status_code == 200, 'bad http response code'
            assert response.result.status == 'COMPLETED', 'tx not completex'
            assert response.result.id == order_id, 'order id does not match'

            purchase = response.result.purchase_units[0]
            srb = purchase.payments.captures[0].seller_receivable_breakdown

            assert srb.paypal_fee.currency_code == 'USD', 'foreign currency'
            assert srb.net_amount.currency_code == 'USD', 'foreign currency'
            assert srb.gross_amount.currency_code == 'USD', 'foreign currency'

            parts = srb.paypal_fee.value.split('.')
            fee = int(parts[0]) * 100 + int(parts[1])
            assert fee > 0, 'invalid fee amount'

            parts = srb.net_amount.value.split('.')
            net = int(parts[0]) * 100 + int(parts[1])
            assert fee > 0, 'invalid net amount'

            parts = srb.gross_amount.value.split('.')
            gross = int(parts[0]) * 100 + int(parts[1])
            assert fee > 0, 'invalid gross amount'

            assert fee + net == gross, 'conversion error'

            description = purchase.payments.captures[0].id
            assert description, 'missing paypal TransactionID'

        except AssertionError as e:
            logger.error(
                'AssertionError while fetching PayPal order: {}'.format(e))
            return '', 0

        return description, net, fee
