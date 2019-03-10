from django.db import models
from model_utils import Choices
from model_utils.models import TimeStampedModel
from model_utils.models import StatusModel, SoftDeletableModel
from profiles.models import Profile

# TODO: best way to handle this? maybe in settings?
CAT_MAX_LEN = 10
TITLE_MAX_LEN = 50
TX_MAX_LEN = 160
DESC_MAX_LEN = 320


class Nonprofit(TimeStampedModel, SoftDeletableModel, StatusModel):
    user = models.OneToOneField(
        Profile,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    CATEGORY = Choices(
        'Animal Rights, Welfare, and Services',
        'Wildlife Conservation',
        'Zoos and Aquariums',
        'Libraries, Historical Societies and Landmark Preservation',
        'Museums',
        'Performing Arts',
        'Public Broadcasting and Media',
        'United Ways',
        'Jewish Federations',
        'Housing and Neighborhood Development',
        'Early Childhood Programs and Services',
        'Youth Education Programs and Services',
        'Adult Education Programs and Services',
        'Special Education',
        'Education Policy and Reform',
        'Scholarship and Financial Support',
        'Environmental Protection and Conservation',
        'Botanical Gardens, Parks, and Nature Centers',
        'Diseases, Disorders, and Disciplines',
        'Patient and Family Support',
        'Treatment and Prevention Services',
        'Medical Research',
        'Advocacy and Education',
        'Children\'s and Family Services',
        'Youth Development, Shelter, and Crisis Services',
        'Food Banks, Food Pantries, and Food Distribution',
        'Multipurpose Human Service Organizations',
        'Homeless Services',
        'Social Services',
        'Development and Relief Services',
        'International Peace, Security, and Affairs',
        'Humanitarian Relief Supplies',
        'Non-Medical Science & Technology Research',
        'Social and Public Policy Research',
        'Religious Activities',
        'Religious Media and Broadcasting',
        'Other',
    )

    category = models.CharField(choices=CATEGORY, max_length=TITLE_MAX_LEN)
    description = models.TextField()

    STATUS = Choices('pending', 'approved')


class Follow(TimeStampedModel):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    target = models.OneToOneField(
        Profile,
        related_name='follower',
        on_delete=models.CASCADE,
    )


class Exchange(TimeStampedModel):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    is_deposit = models.BooleanField()
    amount = models.PositiveIntegerField()


class Post(TimeStampedModel, SoftDeletableModel):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )


class Transaction(StatusModel):
    post = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    target = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )

    amount = models.PositiveIntegerField()
    description = models.CharField(max_length=TX_MAX_LEN)

    STATUS = Choices('requested', 'completed')


class Article(StatusModel):
    post = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    title = models.CharField(max_length=TITLE_MAX_LEN)
    description = models.CharField(max_length=DESC_MAX_LEN)
    content = models.FileField()

    STATUS = Choices('draft', 'published')


class Event(StatusModel):
    post = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    title = models.CharField(max_length=TITLE_MAX_LEN)
    link = models.TextField()
    description = models.CharField(max_length=DESC_MAX_LEN)

    STATUS = Choices('draft', 'published')


class Comment(models.Model):
    post = models.OneToOneField(
        Post,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    parent = models.ForeignKey(
        Post,
        related_name='child',
        on_delete=models.CASCADE,
    )


class Upvote(TimeStampedModel):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
    )


class Downvote(TimeStampedModel):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
    )


class RSVP(TimeStampedModel):
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
    )
