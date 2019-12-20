from django.test import TestCase
from django.core.management import call_command
from graphene.test import Client

import users.models
import ibis.models as models
import api.schema.schema


NUM_PERSON = 10
NUM_DONATION = 100
NUM_TRANSACTION = 100
NUM_NEWS = 100
NUM_EVENT = 100
NUM_POST = 100
NUM_COMMENT = 100
NUM_FOLLOW = 100
NUM_RSVP = 100
NUM_BOOKMARK = 100
NUM_LIKE = 100

call_command(
    'make_fixtures',
    num_person=NUM_PERSON,
    num_donation=NUM_DONATION,
    num_transaction=NUM_TRANSACTION,
    num_news=NUM_NEWS,
    num_event=NUM_EVENT,
    num_post=NUM_POST,
    num_comment=NUM_COMMENT,
    num_follow=NUM_FOLLOW,
    num_rsvp=NUM_RSVP,
    num_bookmark=NUM_BOOKMARK,
    num_like=NUM_LIKE,
)


class GraphQLTestCase(TestCase):
    fixtures = ['fixtures.json']

    # update model state to assume new ground truth
    def set_checkpoint(self):
        self.person_state = {}
        for x in models.Person.objects.all():
            self.person_state[x] = {
                'balance': x.balance(),
                'donated': x.donated(),
                'following': list(x.following.all()),
                'bookmark_for_news': list(x.bookmark_for_news.all()),
                'bookmark_for_post': list(x.bookmark_for_post.all()),
                'rsvp_for_event': list(x.rsvp_for_event.all()),
                'likes_donation': list(x.following.all()),
                'likes_transaction': list(x.likes_transaction.all()),
                'likes_news': list(x.likes_news.all()),
                'likes_event': list(x.likes_event.all()),
                'likes_post': list(x.likes_post.all()),
                'likes_comment': list(x.likes_comment.all()),
            }

        self.nonprofit_state = {}
        for x in models.Nonprofit.objects.all():
            self.person_state[x] = {
                'balance': x.balance(),
                'fundraised': x.fundraised(),
            }

    def setUp(self):
        self.staff = users.models.User.objects.create(
            username='staff',
            first_name='Staffy',
            last_name='McStaffface',
            email='staff@example.come',
            is_staff=True,
        )
        self.set_checkpoint()
        self.client = Client(api.schema.schema)

    def test_setup(self):
        assert len(models.Person.objects.all()) == NUM_PERSON
        assert len(models.Donation.objects.all()) == NUM_DONATION
        assert len(models.Transaction.objects.all()) == NUM_TRANSACTION
        assert len(models.News.objects.all()) == NUM_NEWS
        assert len(models.Event.objects.all()) == NUM_EVENT
        assert len(models.Post.objects.all()) == NUM_POST
        assert len(models.Comment.objects.all()) == NUM_COMMENT

    # --- Positive ---------------------------------------------------------- #

    # staff can do everything
    def test_staff(self):
        pass

    # single object queries for users
    def test_query_single(self):
        pass

    # list queries including sorting for users
    def test_user_query_lists(self):
        pass

    # send money around and verify balances
    def test_money(self):
        pass

    # follow, like, rsvp, and bookmark, monitor sorting effects, and reverse
    def test_edge_mutations(self):
        pass

    # comment and posts
    def test_engagement_mutations(self):
        pass

    # --- Negative ---------------------------------------------------------- #

    # that unauthenticated queries can do nothing
    def test_public(self):
        pass

    # actions using bad model types
    def test_type_constraints(self):
        pass

    # actions that use bad arguments (e.g. uniqueness of blankness)
    def test_arg_constraints(self):
        pass

    # balances below zero and integer overflow
    def test_money_invalid(self):
        pass

    # attempt to access other user's private info
    def test_queries_unauthorized(self):
        pass

    # mutations that users should not allowed to do
    def test_mutations_unauthorized(self):
        pass
