from django.db import models
from rest_framework.exceptions import ValidationError

from flowback.common.models import BaseModel
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Schedule(BaseModel):
    name = models.TextField()
    origin_name = models.CharField(max_length=255)
    origin_id = models.IntegerField()

    active = models.BooleanField(default=True)


class ScheduleEvent(BaseModel):
    # class Recurrence(models.TextChoices):
    #     DAY = ("D", _("Daily"))
    #     WEEK = ("W", _("Weekly"))
    #     MONTH = ("M", _("Monthly"))
    #     YEAR = ("Y", _("Yearly"))

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    title = models.TextField()
    description = models.TextField(null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    work_group = models.ForeignKey('group.WorkGroup', on_delete=models.CASCADE, null=True, blank=True)
    assignees = models.ManyToManyField('group.GroupUser')

    # recurrence_frequency = models.CharField(choices=Recurrence, null=True, blank=True)  # Type of recurrence
    # recurrence_count = models.IntegerField(null=True, blank=True)  # Amount of recurrences
    # recurrence_max = models.IntegerField(null=True, blank=True)  # End recurrence after date

    origin_name = models.CharField(max_length=255)
    origin_id = models.IntegerField()

    def clean(self):
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError('Start date is greater than end date')


class ScheduleSubscription(BaseModel):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='schedule_subscription_schedule')
    target = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='schedule_subscription_target')

    def clean(self):
        if self.schedule == self.target:
            raise ValidationError('Schedule cannot be the same as the target')

    class Meta:
        unique_together = ('schedule', 'target')
