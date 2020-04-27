import logging

from django.utils.timezone import now, timedelta
from django.core.mail import send_mail
from django_cron import CronJobBase, Schedule
from django.conf import settings

from notifications.models import Email

logger = logging.getLogger(__name__)

FREQUENCY = 1


class EmailNotificationCron(CronJobBase):
    schedule = Schedule(run_every_mins=FREQUENCY)
    code = 'notifications.email_notification'

    def do(self):
        # need to be very careful about not accidently spamming users
        # with double sends due exceptions
        for email in Email.objects.filter(status=Email.SCHEDULED):
            if email.schedule < now() - timedelta(minutes=FREQUENCY * 2):
                email.status = Email.STALE
                logger.warning('Stale scheduled emails detected')
            elif email.schedule < now():
                email.status = Email.ATTEMPTING
                destination = email.notification.notifier.user.email
                if email.notification.clicked:
                    email.status = Email.UNNEEDED
                elif destination.split('@')[-1] == 'example.com':
                    logger.info(
                        'Processed fake email to {}'.format(destination))
                    email.status = Email.SUCCEEDED
                else:
                    try:
                        assert send_mail(
                            email.subject,
                            email.body,
                            'Token Ibis<{}>'.format(
                                settings.EMAIL_HOST_USER),
                            [email.notification.notifier.user.email],
                            fail_silently=False,
                            html_message=email.html,
                        )
                        email.status = Email.SUCCEEDED
                    except Exception as e:
                        logger.error(
                            'ERROR: exception sending to {}: {}: {}'.
                            format(
                                email.notification.notifier.user.email,
                                type(e),
                                e,
                            ))
                        email.status = Email.FAILED
            email.save()
