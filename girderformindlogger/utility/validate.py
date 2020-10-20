import json
from functools import wraps
from cerberus import Validator
from girderformindlogger.exceptions import ValidationException


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
