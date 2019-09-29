from django.conf import settings

from paypalcheckoutsdk.core import PayPalHttpClient
from paypalcheckoutsdk.core import SandboxEnvironment, LiveEnvironment
from paypalcheckoutsdk.orders import OrdersGetRequest
from braintreehttp.http_error import HttpError


class PayPalClient:
    def __init__(self):
        if settings.PAYPAL_IS_SANDBOX:
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
            print('HttpError while fetching PayPal order: {}'.format(e))
            return '', 0

        try:
            assert response.result.intent == 'CAPTURE', 'bad payment intent'
            assert response.status_code == 200, 'bad http response code'
            assert response.result.status == 'COMPLETED', 'tx not completex'
            assert response.result.id == order_id, 'order id does not match'

            purchase = response.result.purchase_units[0]

            parts = purchase.amount.value.split('.')
            amount = int(parts[0]) * 100 + int(parts[1])
            assert amount > 0, 'invalid amount'

            payment_id = purchase.payments.captures[0].id
            assert payment_id, 'missing paypal TransactionID'

        except AssertionError as e:
            print('AssertionError while fetching PayPal order: {}'.format(e))
            return '', 0

        return payment_id, amount
