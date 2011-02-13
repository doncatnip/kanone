from .core import Validator
from ..lib import messages

import logging
log = logging.getLogger(__name__)

class Dict(Validator):

    messages\
        ( type="Invalid type, must be a dictionary"
        , convert="Could not convert %s(inputType)s to dict"
        )

    def __init__(self, strict = False):
        self.strict = strict

    def on_value(self, context, value):

        if not isinstance(value, dict):
            if self.strict:
                raise self.invalid( 'type' )
            try:
                value = dict(value)
            except ValueError,TypeError:
                raise self.invalid( 'convert', inputType=value.__class__.__name__ )

        if len( value ) == 0:
            return self.on_blank( context )

        return value

class List(Validator):

    messages\
        ( type="Invalid type, must be a list"
        , convert="Could not convert %(inputType)s to list"
        )

    def __init__(self, strict = False):
        self.strict = strict

    def on_value(self, context, value):
        if isinstance(value,set) or isinstance(value,tuple):
            value = list(value)

        if not isinstance(value, list):
            if self.strict:
                raise self.invalid( 'type' )

            try:
                value = list(value)
            except ValueError,TypeError:
                raise self.invalid( 'convert', inputType=value.__class__.__name__ )

        if len( value ) == 0:
            return self.on_blank( context )

        return value


class Boolean(Validator):

    messages\
        ( type="Invalid type, must be a bool"
        )

    def __init__(self, strict = False):
        self.strict = strict

    def on_value(self, context, value):
        if not isinstance( value, bool ):
            if not self.strict:
                return bool(value)
            raise self.invalid( 'type' )
        return value


class String(Validator):

    messages\
        ( type="Invalid type, must be a string"
        )

    def __init__(self, strip=False, lower=False, update=False, strict=False):
        strip = strip
        lower = lower
        update = update
        strict = strict

    def on_value(self, context, value):

        if isinstance( value, str):
            value = unicode(value)

        if not isinstance( value, unicode):
            if self.strict:
                raise self.invalid( 'type' )
            else:
                value = unicode(value)

        if self.strip:
            value = value.strip()
        if self.lower:
            value = value.lower()

        if self.update:
            context['value'] = value

        return value


class Integer(Validator):

    messages\
        ( type="Invalid type, must be an integer"
        , convert="Could not convert %(inputType)s to integer"
        )

    def __init__(self, strict=False):
        self.strict = strict

    def on_value(self, context, value):
        if not isinstance( value, int ) and not isinstance( value, long):
            if self.strict:
                raise self.invalid( 'type' )
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise self.invalid( 'convert', inputType=value.__class__.__name__ )

        return value

class Float( Integer ):
    messages\
        ( type="Invalid type, must be an integer"
        )

    def __init__(self, strict=False):
        self.strict = strict

    def on_value(self, context, value):
        if not isinstance(value,float):
            if self.strict:
                raise self.invalid('type')
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise self.invalid( 'convert',inputType=value.__class__.__name__ )

        return value
