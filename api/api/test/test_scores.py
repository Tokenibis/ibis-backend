import random
import ibis.models as models

from freezegun import freeze_time
from django.conf import settings
from django.utils.timezone import now, timedelta, utc
from api.test.base import BaseTestCase, TEST_TIME


class ScoreTestCase(BaseTestCase):
    def test_nonprofit_scores(self):
        with freeze_time(
                TEST_TIME.astimezone(utc) + timedelta(7 * (max(
                    settings.SORT_ORGANIZATION_WINDOW_ENTRY,
                    settings.SORT_ORGANIZATION_WINDOW_FUNDRAISED,
                    settings.SORT_ORGANIZATION_WINDOW_JOINED,
                    settings.SORT_ORGANIZATION_WINDOW_RESPONSE,
                )))):

            orgs = random.sample(
                list(
                    models.Organization.objects.exclude(
                        username=settings.IBIS_USERNAME_ROOT)),
                7,
            )

            orgs.sort(key=lambda x: x.score, reverse=True)

            models.Deposit.objects.create(
                user=self.me_person,
                amount=100,
                description='description',
                category=models.ExchangeCategory.objects.first(),
            )

            # give every org two donations
            donations = {
                x: [
                    models.Donation.objects.create(
                        user=self.me_person,
                        target=x,
                        amount=1,
                        description='description',
                    ) for _ in range(2)
                ]
                for x in orgs
            }

            # organization 0 does nothing
            i = 0

            # organization that likes one post only
            i += 1
            donations[orgs[i]][0].like.add(orgs[i])

            # organization that comments one post and likes the other
            i += 1
            donations[orgs[i]][0].like.add(orgs[i])
            models.Comment.objects.create(
                user=orgs[i],
                parent=donations[orgs[i]][1],
                description='thanks!',
            )

            # organization that has posted event only
            i += 1
            models.Event.objects.create(
                user=orgs[i],
                title='title',
                image='image',
                description='description',
                date=now(),
                duration=60,
            )

            # organization that has posted news and likes one post
            i += 1
            models.News.objects.create(
                user=orgs[i],
                title='title',
                image='image',
            )
            donations[orgs[i]][0].like.add(orgs[i])

            # organization that has posted news and likes/comments both
            i += 1
            models.News.objects.create(
                user=orgs[i],
                title='title',
                image='image',
            )
            donations[orgs[i]][0].like.add(orgs[i])
            models.Comment.objects.create(
                user=orgs[i],
                parent=donations[orgs[i]][1],
                description='thanks!',
            )

            # new organization
            i += 1
            orgs[i].date_joined = now()
            orgs[i].save()
            donations[orgs[i]][0].like.add(orgs[i])

            # reload scores
            orgs = [models.Organization.objects.get(id=x.id) for x in orgs]

            for i in range(1, len(orgs)):
                assert orgs[i].score > orgs[i - 1].score
