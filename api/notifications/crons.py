from django.utils.timezone import now, timedelta
from django.core.mail import send_mail
from django_cron import CronJobBase, Schedule
from django.conf import settings

from notifications.models import Email

FREQUENCY = 1


class EmailNotificationCron(CronJobBase):
    schedule = Schedule(run_every_mins=FREQUENCY)
    code = 'notifications.email_notification'

    def do(self):
        # need to be very careful about not accidently spamming users
        # with double sends due exceptions
        for email in Email.objects.all():
            if email.status == Email.SCHEDULED:
                if email.schedule < now() - timedelta(minutes=FREQUENCY * 2):
                    print('WARNING: stale scheduled emails detected')
                elif email.schedule < now():
                    email.status = Email.ATTEMPTING
                    destination = email.notification.notifier.user.email
                    if destination.split('@') == 'example.com':
                        print('Processed fake email to {}'.format(destination))
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
                            )
                            email.status = Email.SUCCEEDED
                        except Exception as e:
                            print('ERROR: exception sending to {}: {}: {}'.
                                  format(
                                      email.notification.notifier.user.email,
                                      type(e),
                                      e,
                                  ))
                            email.status = Email.FAILED
                    email.save()

        Email.objects.filter(status=Email.SUCCEEDED).delete()
