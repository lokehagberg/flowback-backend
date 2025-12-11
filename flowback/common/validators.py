from django.core.exceptions import ValidationError


def FieldNotBlankValidator(value):
    if value and not value.strip():
        raise ValidationError("This field cannot be blank")