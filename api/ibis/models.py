import re

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.conf import settings
from model_utils.models import TimeStampedModel
from graphql_relay.node.node import to_global_id

from users.models import GeneralUser

MIN_USERNAME_LEN = 3
MAX_USERNAME_LEN = 15


def username_validator(value):
    if type(value) != str:
        raise ValidationError('{} is not a string'.format(value))

    if len(value) < MIN_USERNAME_LEN or len(value) > MAX_USERNAME_LEN:
        raise ValidationError('{} is not 3-15 characters long'.format(value))

    if not (value.islower() and value.replace('_', '').isalnum()):
        raise ValidationError(
            '{} has non lower alphanumeric or \'_\' characters'.format(value))

    if value in settings.RESERVED_USERNAMES:
        raise ValidationError('{} is a reserved username'.format(value))


def generate_valid_username(first_name, last_name):
    base = re.sub(
        r'\W+', '', '{} {}'.format(first_name, last_name).strip().replace(
            ' ', '_')).lower()[:MAX_USERNAME_LEN]

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
    privacy_reward = models.BooleanField(default=False)
    gas = models.IntegerField(default=settings.BOT_GAS_INITIAL)
    tank = models.PositiveIntegerField(default=settings.BOT_GAS_INITIAL)


class Person(User):
    class Meta:
        verbose_name = "Person"
        verbose_name_plural = "People"

    reward_from = models.ManyToManyField(
        Bot,
        related_name='reward_to',
        through='Reward',
        symmetrical=False,
    )
    privacy_donation = models.BooleanField(default=False)

    def donated(self):
        return sum([x.amount for x in Donation.objects.filter(user=self)])


class Organization(User):
    category = models.ForeignKey(
        OrganizationCategory,
        on_delete=models.CASCADE,
        null=True,
    )
    link = models.TextField(validators=[MinLengthValidator(1)])
    banner = models.TextField(validators=[MinLengthValidator(1)])

    donation_from = models.ManyToManyField(
        Person,
        related_name='donation_to',
        through='Donation',
        symmetrical=False,
    )

    def fundraised(self):
        return sum([x.amount for x in Donation.objects.filter(target=self)])


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


class Challenge(Entry):
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
    related_challenge = models.ForeignKey(
        Challenge,
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
            self.parent.user,
        )

    def get_root(self):
        current = Entry.objects.get(pk=self.pk)
        while hasattr(current, 'comment'):
            current = current.comment.parent
        return current
