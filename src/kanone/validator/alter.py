from ..lib import messages, Invalid

from .core import Validator, ValidatorBase

class Lower( Validator ):

    messages\
        ( type = u"Values of type %(value.type)s can not be lowered"
        )

    def on_value(self, context, value):
        try:
            return value.lower()
        except Exception:
            raise Invalid( value, self, 'type' )


class Format( Validator ):

    messages\
        ( type = u"Cannot format type %(value.type)s"
        )

    def setParameters( self, formatter, **parameters ):
        self.formatter = formatter
        self.parameters = parameters

    def on_value(self, context, value):
        parameters = dict(self.parameters)
        parameters['value'] = value

        if not isinstance( self.formatter, basestring ):
            raise Invalid( value, self, 'type' )
        try:
            return self.formatter % parameters
        except Exception:
            raise Invalid( value, self )

class DictUpdate( Validator ):

    messages\
        ( type = u"Cannot update type %(value.type)s"
        )

    def setParameters( self, **parameters ):
        self.parameters = parameters

    def on_value(self, context, value ):
        toUpdate = {}
        for (key,param) in self.parameters.iteritems():
            if isinstance(param,ValidatorBase):
                param = param.validate( context, value )
            toUpdate[key] = param
        try:
            value.update( toUpdate )
        except Exception:
            raise Invalid( value, self, 'type' )

        return value

"""
class Replace( Validator ):

    messages\
        ( type = "Can not eliminate white spaces in values of type %(value.type)s"
        )

    def setParameters( self, what, replacement='' ):
        self.what = what
        self.replacement = replacement
        self.whatIsList = isinstance( self.what, list ) or\
            isinstance( self.what, tuple ) or\
            isinstance( self.what, set )

    def on_value( self, context, value):
        try:
            return u''.join(value.split())
        except AttributeError:
            raise self.invalid(context,'type',type=value.__class__.__name__)
"""

class EliminateWhiteSpace( Validator ):

    messages\
        ( type = u"Can not eliminate white spaces in values of type %(value.type)s"
        )


    def on_value( self, context, value):
        try:
            return (''.join(value.split()))
        except AttributeError:
            raise Invalid( value, self, 'type' )


class Strip( Validator ):

    messages\
        ( type = u"Can not strip white spaces in values of type %(value.type)s"
        )


    def on_value( self, context, value):
        try:
            return (value.strip())
        except AttributeError:
            raise Invalid( value, self, 'type' )


class Split( Validator ):

    messages\
        ( type = u"Can not split values of type %(value.type)s"
        )

    def setParameters(self, separator=None, limit=-1):
        self.separator = separator
        self.limit = limit

    def on_value( self, context, value):
        try:
            return value.split( self.separator, self.limit )
        except Exception:
            raise Invalid( value, self, 'type' )


class Join( Validator):

    messages\
        ( type = u"Can not join values of type %(value.type)s"
        )

    def setParameters(self, separator=''):
        self.separator = separator

    def on_value( self, context, value):
        try:
            return self.separator.join( value )
        except Exception:
            raise Invalid( value, self, 'type' )

class Encode( Validator ):

    messages\
        ( type = u"Can not encode %(value.type)s to %(format)s"
        , fail = u"%(value)s cannot be encoded to %(format)s"
        )

    def setParameters( self, format ):
        self.format = format

    def on_value( self, context, value ):
        if not hasattr( value,'encode') or not hasattr( value.encode,'__call__' ):
            raise Invalid( value, self, 'type', format=self.format )

        try:
            value = value.encode( self.format )
        except ValueError:
            raise Invalid( value, self, format=self.format )

        return value

class Decode( Validator ):

    messages\
        ( type = u"Can not decode %(value.type)s to %(format)s"
        , fail = u"%(value)s cannot be decoded to %(format)s"
        )

    def setParameters( self, format ):
        self.format = format

    def on_value( self, context, value ):
        if not hasattr( value,'decode') or not hasattr( value.decode,'__call__' ):
            raise Invalid( value, self, 'type', format=self.format )

        try:
            value = value.decode( self.format )
        except ValueError:
            raise Invalid( value, self, format=self.format )

        return value

class Insert( Validator ):

    messages\
        ( type = u"Unsupported type for insertion (%(value.type)s)"
        , fail = u"Can not insert %(what)s at %(where)i"
        )

    def setParameters( self, what, where=0 ):
        self.what = what
        self.where = where

    def on_value( self, context, value ):
        if ( isinstance( value, basestring ) and isinstance(value,basestring) )\
        or ( isinstance( value, list ) and isinstance( value, list ) ):
            if self.where is 0:
                return self.what + value
            if self.where <0:
                where = self.where-1
            else:
                where = self.where
            return value[0:where] + self.what + value[where:None]

        raise Invalid( value, self,'type' )

class UpdateValue( ValidatorBase ):

    def validate( self, context, value ):
        context.value = value
        return value
