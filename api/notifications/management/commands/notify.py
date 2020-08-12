import logging

from django.core.management.base import BaseCommand
from django.utils.timezone import now, timedelta
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from notifications.models import Email

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send pending notifications'

    def handle(self, *args, **options):
        emails = list(Email.objects.filter(status=Email.SCHEDULED))

        # assumes this for loop completes within one cron job time step
        for email in emails:
            if email.schedule < now() - timedelta(minutes=1 * 2):
                email.status = Email.STALE
                logger.warning('Stale scheduled emails detected')
            elif email.notification.clicked and not email.force:
                email.status = Email.UNNEEDED
            elif email.schedule < now():
                email.status = Email.ATTEMPTING
            email.save()

        # need to be very careful about not accidently spamming users
        # with double sends due exceptions
        for email in emails:
            if email.status == Email.ATTEMPTING:
                # assumes that the cron job runs every 1 minutes
                destination = email.notification.notifier.user.email
                if destination.split('@')[-1] == 'example.com':
                    logger.info(
                        'Processed fake email to {}'.format(destination))
                    email.status = Email.SUCCEEDED
                else:
                    try:
                        msg = EmailMultiAlternatives(
                            email.subject,
                            email.body,
                            'Token Ibis<{}>'.format(settings.EMAIL_HOST_USER),
                            [email.notification.notifier.user.email],
                            headers={
                                'List-Unsubscribe':
                                '<mailto: {}>, <{}{}>'.format(
                                    settings.UNSUBSCRIBE_EMAIL,
                                    settings.API_ROOT_PATH,
                                    email.notification.notifier.
                                    create_unsubscribe_link(),
                                ),
                            },
                        )
                        msg.attach_alternative(email.html, 'text/html')
                        msg.send()
                        email.status = Email.SUCCEEDED
                    except Exception as e:
                        logger.error(
                            'ERROR: exception sending to {}: {}: {}'.format(
                                email.notification.notifier.user.email,
                                type(e),
                                e,
                            ))
                        email.status = Email.FAILED
                email.save()
