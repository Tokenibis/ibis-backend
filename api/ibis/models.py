from django.db import models
from django.core.validators import MinLengthValidator
from model_utils.models import TimeStampedModel, SoftDeletableModel

from users.models import User


class Scoreable(models.Model):
    score = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True


class IbisUser(User, Scoreable):
    class Meta:
        verbose_name_plural = 'ibis user'

    following = models.ManyToManyField(
        'self',
        related_name='follower',
        symmetrical=False,
        blank=True,
    )
    avatar = models.TextField(validators=[MinLengthValidator(1)])

    def __str__(self):
        return '{}{}{}'.format(
            self.first_name,
            ' ' if self.first_name and self.last_name else '',
            self.last_name,
        )

    def balance(self):
        raise NotImplementedError

    def can_see(self, entry):
        if hasattr(entry, 'comment'):
            entry = entry.comment.get_root()

        if hasattr(entry, 'donation') and hasattr(entry.user, 'person'):
            permission = entry.user.person.visibility_donation
            if permission == Person.PRIVATE:
                return self.id == entry.user.person.id
            if permission == Person.FOLLOWING:
                return entry.user.following.filter(pk=self.id).exists()

        if hasattr(entry, 'transaction') and hasattr(entry.user, 'person'):
            permission = entry.user.person.visibility_transaction
            if permission == Person.PRIVATE:
                return self.id == entry.user.person.id
            if permission == Person.FOLLOWING:
                return entry.self.following.filter(pk=self.id).exists()

        return True


class Valuable(models.Model):
    amount = models.PositiveIntegerField()

    class Meta:
        abstract = True


class Likeable(models.Model):
    like = models.ManyToManyField(
        IbisUser,
        related_name='likes_%(class)s',
        blank=True,
    )

    class Meta:
        abstract = True


class Bookmarkable(models.Model):
    bookmark = models.ManyToManyField(
        IbisUser,
        related_name='bookmark_for_%(class)s',
        blank=True,
    )

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

    PUBLIC = 'PC'
    FOLLOWING = 'FL'
    PRIVATE = 'PR'

    VISIBILITY_CHOICES = (
        (PUBLIC, 'Public'),
        (FOLLOWING, 'Following Only'),
        (PRIVATE, 'Me Only'),
    )

    transaction_to = models.ManyToManyField(
        IbisUser,
        related_name='transaction_from',
        through='Transaction',
        symmetrical=False,
    )

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

    def balance(self):
        deposit = sum([ex.amount for ex in self.deposit_set.all()])
        donation = sum([x.amount for x in Donation.objects.filter(user=self)])
        transaction_in = sum(
            [x.amount for x in Transaction.objects.filter(target=self)])
        transaction_out = sum(
            [x.amount for x in Transaction.objects.filter(user=self)])
        return (deposit) + (transaction_in - transaction_out) - (donation)

    def donated(self):
        return sum([x.amount for x in Donation.objects.filter(user=self)])


class Nonprofit(IbisUser, TimeStampedModel, SoftDeletableModel):
    class Meta:
        verbose_name = "Nonprofit"

    title = models.TextField(unique=True, validators=[MinLengthValidator(1)])
    category = models.ForeignKey(
        NonprofitCategory,
        on_delete=models.CASCADE,
    )
    description = models.TextField(validators=[MinLengthValidator(1)])
    link = models.TextField(validators=[MinLengthValidator(1)])
    banner = models.TextField(validators=[MinLengthValidator(1)])

    donation_from = models.ManyToManyField(
        IbisUser,
        related_name='donation_to',
        through='Donation',
        symmetrical=False,
    )

    def __str__(self):
        return self.title

    def balance(self):
        deposit = sum([ex.amount for ex in self.deposit_set.all()])
        withdrawal = sum([ex.amount for ex in self.withdrawal_set.all()])
        donation_in = sum(
            [x.amount for x in Donation.objects.filter(target=self)])
        transaction_out = sum(
            [x.amount for x in Transaction.objects.filter(user=self)])
        return (deposit - withdrawal) + (donation_in - transaction_out)

    def fundraised(self):
        return sum([x.amount for x in Donation.objects.filter(target=self)])


class Entry(TimeStampedModel, SoftDeletableModel):
    class Meta:
        verbose_name = "Entry"
        verbose_name_plural = "Entries"

    user = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )
    description = models.TextField(validators=[MinLengthValidator(1)])


class Deposit(TimeStampedModel, Valuable):
    user = models.ForeignKey(
        IbisUser,
        on_delete=models.CASCADE,
    )
    payment_id = models.TextField(
        unique=True, validators=[MinLengthValidator(1)])


class Withdrawal(Valuable):
    user = models.ForeignKey(
        Nonprofit,
        on_delete=models.CASCADE,
    )


class Donation(Entry, Valuable, Likeable, Scoreable):
    target = models.ForeignKey(
        Nonprofit,
        on_delete=models.CASCADE,
    )


class Transaction(Entry, Valuable, Likeable, Scoreable):
    target = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
    )


class News(Entry, Likeable, Bookmarkable, Scoreable):
    class Meta:
        verbose_name_plural = 'news'

    title = models.TextField(validators=[MinLengthValidator(1)])
    link = models.TextField(validators=[MinLengthValidator(1)])
    image = models.TextField(validators=[MinLengthValidator(1)])

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Event(Entry, Likeable, Bookmarkable, Rsvpable, Scoreable):
    title = models.TextField(validators=[MinLengthValidator(1)])
    link = models.TextField(validators=[MinLengthValidator(1)])
    image = models.TextField(validators=[MinLengthValidator(1)])
    address = models.TextField(validators=[MinLengthValidator(1)])
    date = models.DateTimeField()

    def __str__(self):
        return '{} ({})'.format(self.title, self.id)


class Post(Entry, Likeable, Bookmarkable, Scoreable):
    title = models.TextField(validators=[MinLengthValidator(1)])


class Comment(Entry, Likeable, Scoreable):
    parent = models.ForeignKey(
        Entry,
        related_name='parent_of',
        on_delete=models.CASCADE,
    )

    def get_root(self):
        current = Entry.objects.get(pk=self.pk)
        while hasattr(current, 'comment'):
            current = current.comment.parent
        return current
