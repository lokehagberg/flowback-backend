from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from flowback.common.models import BaseModel


class PredictionStatement(BaseModel):
    description = models.TextField(max_length=2000)
    end_date = models.DateTimeField()
    # created_by: represents ownership
    # fk: represents relationship

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
    # prediction_statement: represents prediction statement
    # created_by: represents ownership

    class Meta:
        abstract = True
