import os
import time
import unicodedata
import regex as re

from PIL import Image
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import models
from django.utils.timezone import localtime, timedelta
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.conf import settings
from model_utils.models import TimeStampedModel
from graphql_relay.node.node import to_global_id
from api.utils import get_submodel

from users.models import GeneralUser

MIN_USERNAME_LEN = 3
MAX_USERNAME_LEN = 15


def store_image(upload, directory, thumbnail_size=None):
    tmp = os.path.join(
        settings.MEDIA_ROOT,
        default_storage.save(
            os.path.join(directory, 'tmp'),
            ContentFile(upload.read()),
        ),
    )
    try:
        im = Image.open(tmp)
        if thumbnail_size:
            im.thumbnail(thumbnail_size)
        path = '{}/{}.png'.format(
            tmp.rsplit('/', 1)[0],
            int(time.time()),
        )
        im.save(path)

        url = '{}{}{}'.format(
            settings.API_ROOT_PATH,
            settings.MEDIA_URL,
            '/'.join(path.rsplit('/')[-3:]),
        )
    except Exception as e:
        raise e
    finally:
        os.remove(tmp)
        return url


def _normalize_username(value):
    return unicodedata.normalize('NFD', value).encode(
        'ascii',
        'ignore',
    ).decode()


def username_validator(value):
    if type(value) != str:
        raise ValidationError('{} is not a string'.format(value))

    if len(value) < MIN_USERNAME_LEN or len(value) > MAX_USERNAME_LEN:
        raise ValidationError('{} is not 3-15 characters long'.format(value))

    if not (value.islower() and value.replace('_', '').isalnum()
            and value == _normalize_username(value)):
        raise ValidationError(
            '{} has non lower alphanumeric or \'_\' characters'.format(value))

    if value in settings.RESERVED_USERNAMES:
        raise ValidationError('{} is a reserved username'.format(value))


def generate_valid_username(first_name, last_name):
    base = _normalize_username(
        re.sub(r'\W+',
               '', '{} {}'.format(first_name, last_name).strip().replace(
                   ' ', '_')).lower()[:MAX_USERNAME_LEN])

    if len(base) < MIN_USERNAME_LEN:
        base = '___'

    name = base
    index = 1

    while User.objects.filter(username=name).exists():
        index += 1
        suffix = '_{}'.format(index)
        name = base[:MAX_USERNAME_LEN - len(suffix)] + suffix

    return name


class Scoreable(models.Model):
    score = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True


class Hideable(models.Model):
    private = models.BooleanField(default=False)

    class Meta:
        abstract = True


class User(GeneralUser, Scoreable):
    class Meta:
        verbose_name_plural = 'ibis user'

    following = models.ManyToManyField(
        'self',
        related_name='follower',
        symmetrical=False,
        blank=True,
    )

    avatar = models.TextField(validators=[MinLengthValidator(1)])
    description = models.TextField(blank=True, null=True)
    scratch = models.TextField(blank=True, null=True)
    referral = models.TextField(blank=True, null=True)

    def __str__(self):
        return '{}{}{}'.format(
            self.first_name,
            ' ' if self.first_name and self.last_name else '',
            self.last_name,
        )

    def balance(self):
        return sum([
            +sum([x.amount for x in Deposit.objects.filter(user=self.id)]),
            +sum([x.amount for x in Donation.objects.filter(target=self.id)]),
            +sum([x.amount for x in Reward.objects.filter(target=self.id)]),
            -sum([x.amount for x in Donation.objects.filter(user=self.id)]),
            -sum([x.amount for x in Reward.objects.filter(user=self.id)]),
            -sum([x.amount for x in Withdrawal.objects.filter(user=self.id)]),
        ])

    def can_see(self, entry):
        if hasattr(entry, 'comment'):
            entry = entry.comment.get_root()

        if hasattr(entry, 'donation') and entry.donation.private:
            return self.id == entry.donation.user.id or self.id == entry.donation.target.id

        if hasattr(entry, 'reward') and entry.reward.private:
            return self.id == entry.reward.user.id or self.id == entry.reward.target.id

        return True

    def clean(self):
        username_validator(self.username)


class Valuable(models.Model):
    amount = models.PositiveIntegerField()

    class Meta:
        abstract = True


class Rsvpable(models.Model):
    rsvp = models.ManyToManyField(
        User,
        related_name='rsvp_for_%(class)s',
        blank=True,
    )

    class Meta:
        abstract = True


class OrganizationCategory(models.Model):
    class Meta:
        verbose_name_plural = 'organization categories'

    title = models.TextField(unique=True, validators=[MinLengthValidator(1)])
    description = models.TextField(validators=[MinLengthValidator(1)])

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Bot(User):
    class Meta:
        verbose_name = "Bot"
        verbose_name_plural = "Bots"

    privacy_reward = models.BooleanField(default=False)
    gas = models.IntegerField(default=settings.BOT_GAS_INITIAL)
    tank = models.PositiveIntegerField(default=settings.BOT_GAS_INITIAL)

    def rewarded(self):
        return sum([x.amount for x in Reward.objects.filter(user=self)])


class Person(User):
    class Meta:
        verbose_name = "Person"
        verbose_name_plural = "People"

    privacy_donation = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    verified_original = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True)

    def donated(self):
        return sum([x.amount for x in Donation.objects.filter(user=self)])


class Organization(User):
    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    category = models.ForeignKey(
        OrganizationCategory,
        on_delete=models.CASCADE,
        null=True,
    )
    link = models.TextField(validators=[MinLengthValidator(1)])
    banner = models.TextField(validators=[MinLengthValidator(1)])

    def fundraised(self):
        return sum([x.amount for x in Donation.objects.filter(target=self)])

    def fundraised_recently(self):
        return sum(
            x.amount for x in Donation.objects.filter(
                target=self,
                created__gte=localtime() - timedelta(
                    days=7 * settings.SORT_ORGANIZATION_WINDOW_FUNDRAISED),
            ))

    def has_recent_entry(self):
        return News.objects.filter(
            user=self,
            created__gte=localtime() -
            timedelta(days=7 * settings.SORT_ORGANIZATION_WINDOW_ENTRY),
        ).exists() or Event.objects.filter(
            user=self,
            created__gte=localtime() -
            timedelta(days=7 * settings.SORT_ORGANIZATION_WINDOW_ENTRY),
        ).exists()

    def recent_response_rate(self):
        donations = Donation.objects.filter(
            target=self,
            created__gte=localtime() -
            timedelta(days=7 * settings.SORT_ORGANIZATION_WINDOW_RESPONSE),
        )

        if not donations.count():
            return 0.0

        return sum(1 for x in donations if x.like.filter(
            id=self.id).exists() or Comment.objects.filter(
                user=self,
                parent=x,
            ).exists()) / donations.count()


class Entry(TimeStampedModel, Scoreable):
    class Meta:
        verbose_name = "Entry"
        verbose_name_plural = "Entries"

    description = models.TextField(validators=[MinLengthValidator(1)])

    bookmark = models.ManyToManyField(
        User,
        related_name='bookmark_for',
        blank=True,
    )

    like = models.ManyToManyField(
        User,
        related_name='likes',
        blank=True,
    )

    mention = models.ManyToManyField(
        User,
        related_name='mentioned_by',
        blank=True,
    )

    scratch = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if (hasattr(self, 'donation')
                and self.donation.private) or (hasattr(self, 'reward')
                                               and self.reward.private):
            return super().save(*args, **kwargs)

        mention = set(
            User.objects.get(username=x[2:-1]) for x in re.findall(
                r'\W@\w{{{},{}}}\W'.format(
                    MIN_USERNAME_LEN,
                    MAX_USERNAME_LEN,
                ),
                ' ' + self.description + ' ',
                overlapped=True,
            ) if User.objects.filter(username=x[2:-1]).exists())

        for x in mention:
            self.description = re.sub(
                r'(\W)@{}(\W)'.format(x.username),
                r'\1@{}\2'.format(to_global_id('UserNode', str(x.id))),
                ' ' + self.description + ' ',
            )[1:-1]

        super().save(*args, **kwargs)

        for x in self.mention.all():
            if x not in mention and not re.findall(
                    r'\W@{}\W'.format(
                        re.escape(to_global_id(
                            'UserNode',
                            str(x.id),
                        ))),
                    ' ' + self.description + ' ',
                    overlapped=True,
            ):
                self.mention.remove(x)

        for user in [
                x for x in mention
                if not self.mention.filter(id=x.id).exists()
        ]:
            self.mention.add(user)

    def resolve_description(self):
        description = self.description
        for x in self.mention.all():
            description = re.sub(
                r'(\W)@{}(\W)'.format(
                    re.escape(to_global_id(
                        'UserNode',
                        str(x.id),
                    ))),
                r'\1@{}\2'.format(x.username),
                ' ' + description + ' ',
            )[1:-1]
        return description


class ExchangeCategory(models.Model):
    class Meta:
        verbose_name_plural = 'Exchange categories'

    title = models.TextField(unique=True, validators=[MinLengthValidator(1)])

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Exchange(TimeStampedModel, Valuable):
    class Meta:
        abstract = True

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    category = models.ForeignKey(
        ExchangeCategory,
        on_delete=models.CASCADE,
    )
    description = models.TextField()

    def __str__(self):
        return '{}:{}:{:.2f}'.format(
            self.pk,
            self.user,
            self.amount / 100,
        )


class Deposit(Exchange):
    pass


class Withdrawal(Exchange):
    pass


class News(Entry):
    class Meta:
        verbose_name_plural = 'news'

    user = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
    )
    title = models.TextField(validators=[MinLengthValidator(1)])
    image = models.TextField(validators=[MinLengthValidator(1)])
    link = models.TextField(blank=True)

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Event(Entry, Rsvpable):
    user = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
    )
    title = models.TextField(validators=[MinLengthValidator(1)])
    image = models.TextField(validators=[MinLengthValidator(1)])
    address = models.TextField(blank=True)
    date = models.DateTimeField()
    duration = models.PositiveIntegerField()
    link = models.TextField(blank=True)
    virtual = models.BooleanField(default=False)

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Donation(Entry, Valuable, Hideable):
    user = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
    )
    target = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return '{}:{}->{}:{:.2f}'.format(
            self.pk,
            self.user,
            self.target,
            self.amount / 100,
        )


class Post(Entry):
    user = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
    )
    title = models.TextField(validators=[MinLengthValidator(1)])


class Activity(Entry):
    class Meta:
        verbose_name_plural = 'Activities'

    user = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE,
    )
    title = models.TextField(validators=[MinLengthValidator(1)])
    active = models.BooleanField()
    reward_min = models.PositiveIntegerField(default=0)
    reward_range = models.PositiveIntegerField(default=0)


class Reward(Entry, Valuable, Hideable):
    user = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE,
    )
    target = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
    )
    related_activity = models.ForeignKey(
        Activity,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return '{}:{}->{}:{:.2f}'.format(
            self.pk,
            self.user,
            self.target,
            self.amount / 100,
        )


class Comment(Entry):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    parent = models.ForeignKey(
        Entry,
        related_name='parent_of',
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return '{}:{}->{}'.format(
            self.pk,
            self.user,
            get_submodel(self.parent).objects.get(id=self.parent.id).user,
        )

    def get_root(self):
        current = Entry.objects.get(pk=self.pk)
        while hasattr(current, 'comment'):
            current = current.comment.parent
        return current


class Channel(TimeStampedModel):
    name = models.TextField(unique=True, validators=[MinLengthValidator(1)])
    member = models.ManyToManyField(
        User,
        blank=True,  # no members implies public channel
    )
    subscriber = models.ManyToManyField(
        User,
        blank=True,
        related_name='subscribe_to',
    )


class Message(TimeStampedModel):
    class Meta:
        abstract = True

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    description = models.TextField(validators=[MinLengthValidator(1)])

    def __str__(self):
        return '{} -> {}'.format(self.user, self.target)


class MessageDirect(Message):
    class Meta:
        verbose_name_plural = 'Messages Direct'

    target = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='message_received',
    )


class MessageChannel(Message):
    class Meta:
        verbose_name_plural = 'Messages Channel'

    target = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name='message_received',
    )


class Investment(TimeStampedModel, Valuable):
    name = models.TextField()
    start = models.DateField()
    end = models.DateField()
    description = models.TextField(blank=True, null=True)
    funded = models.ManyToManyField(
        Donation,
        related_name='funded_by',
        through='DonationInvestment',
        blank=True,
    )
    user = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='invested',
        null=True,
        blank=True,
    )

    @property
    def info_str(self):
        amounts = sum(x.amount for x in self.funded.all())

        return '\n'.join('{}: {}'.format(x, y) for x, y in [
            ('Total Investment', '${:.2f}'.format(self.amount / 100)),
            ('Donations Funded', self.funded.count()),
            ('Spending Timeline', '{} to {}'.format(self.start, self.end)),
            ('Percent Spent',
             '{}%'.format(min(100, round(100 * amounts / self.amount)))),
        ])

    def __str__(self):
        return '{} ${:.2f} {} - {}'.format(
            self.name,
            self.amount / 100,
            self.start,
            self.end,
        )


class DonationInvestment(Valuable):
    investment = models.ForeignKey(
        Investment,
        on_delete=models.CASCADE,
    )
    donation = models.ForeignKey(
        Donation,
        on_delete=models.CASCADE,
    )
