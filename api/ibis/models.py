from datetime import datetime

from django.db import models


class Account(models.Model):
    nickname = models.CharField(max_length=32)
    create_time = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return '{}({})'.format(self.nickname, self.id)


class Transaction(models.Model):

    sender = models.ForeignKey(
        Account, related_name='sender', on_delete=models.CASCADE)
    receiver = models.ForeignKey(
        Account, related_name='receiver', on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=6, decimal_places=2)
    datetime = models.DateTimeField(default=datetime.now)
    description = models.TextField()

    def __str__(self):
        return '{} - {} - {}'.format(self.sender, self.receiver, self.datetime)
