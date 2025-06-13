from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from flowback.common.models import BaseModel
from flowback.files.models import FileCollection


class PredictionStatement(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(max_length=2000, null=True, blank=True)
    end_date = models.DateTimeField()
    # created_by: represents ownership
    # fk: represents relationship
    combined_bet = models.DecimalField(max_digits=8, decimal_places=7, null=True, blank=True)
    outcome = models.BooleanField(default=False, null=True, blank=True)
    attachments = ArrayField(models.FileField(upload_to='group/poll/prediction/attachments'),
                             null=True,
                             blank=True,
                             max_length=10)
    blockchain_id = models.PositiveIntegerField(null=True, blank=True, default=None)

    class Meta:
        abstract = True


class PredictionStatementSegment(BaseModel):
    is_true = models.BooleanField()
    # prediction_statement: represents prediction statement
    # fk: represents relationship

    class Meta:
        abstract = True


class PredictionStatementVote(BaseModel):
    vote = models.BooleanField()
    # prediction_statement: represents prediction statement
    # created_by: represents ownership

    class Meta:
        abstract = True


class PredictionBet(BaseModel):
    score = models.IntegerField(validators=[MaxValueValidator(5), MinValueValidator(0)])
    blockchain_id = models.PositiveIntegerField(null=True, blank=True, default=None)
    # prediction_statement: represents prediction statement
    # created_by: represents ownership

    class Meta:
        abstract = True
