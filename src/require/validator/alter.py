from ..lib import messages, MISSING, Invalid

from .core import Validator, ValidatorBase

class Lower( Validator ):

    messages\
        ( type = "Values of type %(type)s can not be lowered"
        )

    def on_value(self, context, value):
        try:
            return value.lower()
        except Exception,e:
            raise self.invalid(context,'type',type=value.__class__.__name__)


class EliminateWhiteSpace( Validator ):

    messages\
        ( type = "Can not eliminate white spaces in values of type %(type)s"
        )

    def on_value( self, context, value):
        try:
            return u''.join(value.split())
        except Exception,e:
            raise self.invalid(context,'type',type=value.__class__.__name__)


class Split( Validator ):

    messages\
        ( type = "Can not split values of type %(type)s"
        )

    def setParameters(self, separator=None, limit=-1):
        self.separator = separator
        self.limit = limit

    def on_value( self, context, value):
        try:
            return value.split( self.separator, self.limit )
        except Exception,e:
            raise self.invalid(context,'type',type=value.__class__.__name__)


class Join( Validator):

    messages\
        ( type = "Can not join values of type %(type)s"
        )

    def setParameters(self, separator=''):
        self.separator = separator

    def on_value( self, context, value):
        try:
            return self.separator.join( value )
        except Exception,e:
            raise self.invalid(context,'type',type=value.__class__.__name__)

class Encode( Validator ):

    messages\
        ( type = "Can not encode %(type)s to %(format)s"
        , fail = "%(value)s cannot be encoded to %(format)s"
        )

    def setParameters( self, format ):
        self.format = format

    def on_value( self, context, value ):
        if not hasattr( value,'encode') or not hasattr( value.encode,'__call__' ):
            raise self.invalid(context, 'type', format=self.format, type=value.__class__.__name__ )

        try:
            value = value.encode( self.format )
        except ValueError:
            raise self.invalid( context,format=self.format )

        return value

class Insert( Validator ):

    messages\
        ( type = "Unsupported type for insertion (%(type)s)"
        , fail = "Can not insert %(what)s at %(where)i"
        )

    def setParameters( self, what, where=0 ):
        self.what = what
        self.where = where

    def on_value( self, context, value ):
        result = value
        if ( isinstance( value, basestring ) and isinstance(value,basestring) )\
        or ( isinstance( value, list ) and isinstance( value, list ) ):
            if self.where is 0:
                return self.what + value
            if self.where <0:
                where = self.where-1
            else:
                where = self.where
            return value[0:where] + self.what + value[where:None]

        raise self.invalid( context,'type', type=value.__class__.__name__ )

class UpdateValue( ValidatorBase ):

    def validate( self, context, value ):
        context['value'] = value
        return value
