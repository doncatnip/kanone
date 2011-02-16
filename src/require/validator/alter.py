from ..lib import messages, MISSING, Invalid

from .core import Validator

class Lower( Validator ):

    messages\
        ( type = "Values of type %(type)s can not be lowered"
        )

    def on_value(self, context, value):
        try:
            return value.lower()
        except Exception,e:
            raise Invalid('type',type=value.__class__.__name__)


class EliminateWhiteSpace( Validator ):

    messages\
        ( type = "Can not eliminate white spaces in values of type %(type)s"
        )

    def on_value( self, context, value):
        try:
            return u''.join(value.split())
        except Exception,e:
            raise Invalid('type',type=value.__class__.__name__)

class Split( Validator ):

    messages\
        ( type = "Can not split values of type %(type)s"
        )

    def __init__(self, separator=None, limit=-1):
        self.separator = separator
        self.limit = limit

    def on_value( self, context, value):
        try:
            return value.split( self.separator, self.limit )
        except Exception,e:
            raise Invalid('type',type=value.__class__.__name__)

class Join( Validator):

    messages\
        ( type = "Can not join values of type %(type)s"
        )

    def __init__(self, separator=''):
        self.separator = separator

    def on_value( self, context, value):
        try:
            return self.separator.join( value )
        except Exception,e:
            raise Invalid('type',type=value.__class__.__name__)
