import re

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.conf import settings
from model_utils.models import TimeStampedModel
from graphql_relay.node.node import to_global_id

from users.models import User

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

    while IbisUser.objects.filter(username=name).exists():
        index += 1
        suffix = '_{}'.format(index)
        name = base[:MAX_USERNAME_LEN - len(suffix)] + suffix

    return name


class Scoreable(models.Model):
    score = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True


class IbisUser(User, Scoreable):
    class Meta:
        verbose_name_plural = 'ibis user'

    PUBLIC = 'PC'
    FOLLOWING = 'FL'
    PRIVATE = 'PR'

    VISIBILITY_CHOICES = (
        (PUBLIC, 'Public'),
        (FOLLOWING, 'Following Only'),
        (PRIVATE, 'Me Only'),
    )

    following = models.ManyToManyField(
        'self',
        related_name='follower',
        symmetrical=False,
        blank=True,
    )

    avatar = models.TextField(validators=[MinLengthValidator(1)])
    description = models.TextField(blank=True, null=True)

    visibility_donation = models.CharField(
        max_length=2,
        choices=VISIBILITY_CHOICES,
        default=PUBLIC,
    )

    visibility_transaction = models.CharField(
        max_length=2,
        choices=VISIBILITY_CHOICES,
        default=PUBLIC,
    )

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
            +sum(
                [x.amount
                 for x in Transaction.objects.filter(target=self.id)]),
            -sum([x.amount for x in Donation.objects.filter(user=self.id)]),
            -sum([x.amount for x in Transaction.objects.filter(user=self.id)]),
            -sum([x.amount for x in Withdrawal.objects.filter(user=self.id)]),
        ])

    def donated(self):
        return sum([x.amount for x in Donation.objects.filter(user=self)])

    def can_see(self, entry):
        if hasattr(entry, 'comment'):
            entry = entry.comment.get_root()

        if hasattr(entry, 'donation'):
            permission = entry.user.visibility_donation
            if permission == IbisUser.PRIVATE:
                return self.id == entry.user.id
            if permission == IbisUser.FOLLOWING:
                return entry.user.following.filter(pk=self.id).exists()

        if hasattr(entry, 'transaction'):
            permission = entry.user.visibility_transaction
            if permission == IbisUser.PRIVATE:
                return self.id == entry.user.id
            if permission == IbisUser.FOLLOWING:
                return entry.self.following.filter(pk=self.id).exists()

        return True

    def clean(self):
        username_validator(self.username)


class Valuable(models.Model):
    amount = models.PositiveIntegerField()

    class Meta:
        abstract = True


class Rsvpable(models.Model):
    rsvp = models.ManyToManyField(
        IbisUser,
        related_name='rsvp_for_%(class)s',
        blank=True,
    )

    class Meta:
        abstract = True


class NonprofitCategory(models.Model):
    class Meta:
        verbose_name_plural = 'nonprofit categories'

    title = models.TextField(unique=True, validators=[MinLengthValidator(1)])
    description = models.TextField(validators=[MinLengthValidator(1)])

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Person(IbisUser):
    class Meta:
        verbose_name = "Person"
        verbose_name_plural = "People"

    transaction_from = models.ManyToManyField(
        IbisUser,
        related_name='transaction_to',
        through='Transaction',
        symmetrical=False,
    )
    is_bot = models.BooleanField(default=False)


class Nonprofit(IbisUser):
    class Meta:
        verbose_name = "Nonprofit"

    category = models.ForeignKey(
        NonprofitCategory,
        on_delete=models.CASCADE,
    )
    link = models.TextField(validators=[MinLengthValidator(1)])
    banner = models.TextField(validators=[MinLengthValidator(1)])

    donation_from = models.ManyToManyField(
        IbisUser,
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

    user = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )

    description = models.TextField(validators=[MinLengthValidator(1)])

    bookmark = models.ManyToManyField(
        IbisUser,
        related_name='bookmark_for',
        blank=True,
    )

    like = models.ManyToManyField(
        IbisUser,
        related_name='likes',
        blank=True,
    )

    mention = models.ManyToManyField(
        IbisUser,
        related_name='mentioned_by',
        blank=True,
    )

    def save(self, *args, **kwargs):
        mention = set(
            IbisUser.objects.get(username=x[2:-1]) for x in re.findall(
                r'\W@\w{{{},{}}}\W'.format(
                    MIN_USERNAME_LEN,
                    MAX_USERNAME_LEN,
                ),
                ' ' + self.description + ' ',
            ) if IbisUser.objects.filter(username=x[2:-1]).exists())

        for x in mention:
            self.description = re.sub(
                r'(\W)@{}(\W)'.format(x.username),
                r'\1@{}\2'.format(to_global_id('IbisUserNode', str(x.id))),
                ' ' + self.description + ' ',
            )[1:-1]

        super().save(*args, **kwargs)

        for x in self.mention.all():
            if x not in mention and not re.findall(
                    r'\W@{}\W'.format(
                        re.escape(to_global_id(
                            'IbisUserNode',
                            str(x.id),
                        ))),
                    ' ' + self.description + ' ',
            ):
                print('removing for some reason')
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
                        'IbisUserNode',
                        str(x.id),
                    ))),
                r'\1@{}\2'.format(x.username),
                ' ' + description + ' ',
            )[1:-1]
        return description


class DepositCategory(models.Model):
    class Meta:
        verbose_name_plural = 'deposit categories'

    title = models.TextField(unique=True, validators=[MinLengthValidator(1)])

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Deposit(TimeStampedModel, Valuable):
    user = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )
    category = models.ForeignKey(
        DepositCategory,
        on_delete=models.CASCADE,
    )
    payment_id = models.TextField(
        unique=True, validators=[MinLengthValidator(1)])

    def __str__(self):
        return '{}:{}:{:.2f}'.format(
            self.pk,
            self.user,
            self.amount / 100,
        )


class Withdrawal(TimeStampedModel, Valuable):
    user = models.ForeignKey(
        Nonprofit,
        on_delete=models.CASCADE,
    )
    description = models.TextField(blank=True)

    def __str__(self):
        return '{}:{}:{:.2f}'.format(
            self.pk,
            self.user,
            self.amount / 100,
        )


class Donation(Entry, Valuable):
    target = models.ForeignKey(
        Nonprofit,
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return '{}:{}->{}:{:.2f}'.format(
            self.pk,
            self.user,
            self.target,
            self.amount / 100,
        )


class Transaction(Entry, Valuable):
    target = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return '{}:{}->{}:{:.2f}'.format(
            self.pk,
            self.user,
            self.target,
            self.amount / 100,
        )


class News(Entry):
    class Meta:
        verbose_name_plural = 'news'

    title = models.TextField(validators=[MinLengthValidator(1)])
    image = models.TextField(validators=[MinLengthValidator(1)])
    link = models.TextField(blank=True)

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Event(Entry, Rsvpable):
    title = models.TextField(validators=[MinLengthValidator(1)])
    image = models.TextField(validators=[MinLengthValidator(1)])
    address = models.TextField(blank=True)
    date = models.DateTimeField()
    duration = models.PositiveIntegerField()
    link = models.TextField(blank=True)

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Post(Entry):
    title = models.TextField(validators=[MinLengthValidator(1)])


class Comment(Entry):
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
