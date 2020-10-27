import re
import json
from functools import wraps
from cerberus import Validator
from girderformindlogger.exceptions import ValidationException


def email_validator(field, value, error):
    if re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', value):
        error(field, "Incorrect email format")


def symbol_validator(field, value, error):
    if re.match(r'(?=.*[!@#$%^&*<>{}])', value):
        error(field, "Field contains incorrect symbols")


def validator(schema):
    def _wrapper(f):
        @wraps(f)
        def validate(*args, **kwargs):
            v = Validator(schema)
            params = kwargs
            if len(args):
                params = dict(zip(schema.keys(), args))
            if v.validate(params):
                f(*args, **kwargs)
            else:
                raise ValidationException(json.dumps(v.errors))
        return validate
    return _wrapper
