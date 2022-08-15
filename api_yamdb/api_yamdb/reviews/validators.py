from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def username_not_me(value):
    if value == 'me':
        raise ValidationError(
            _('username cannot be "me"'),
            params={'value': value},
        )
