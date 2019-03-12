from ..lib import Invalid

from .core import Validator, ValidatorBase, messages

@messages\
    ( type = "Values of type %(value.type)s can not be lowered"
    )
class Lower( Validator ):


    def on_value(self, context, value):
        try:
            return value.lower()
        except Exception:
            raise Invalid( value, self, 'type' )

@messages\
    ( type = "Cannot format type %(value.type)s"
    )
class Format( Validator ):


    def setParameters( self, formatter, **parameters ):
        self.formatter = formatter
        self.parameters = parameters

    def on_value(self, context, value):
        parameters = dict(self.parameters)
        parameters['value'] = value

        if not isinstance( self.formatter, str ):
            raise Invalid( value, self, 'type' )
        try:
            return self.formatter % parameters
        except Exception:
            raise Invalid( value, self )
@messages\
    ( type = "Cannot update type %(value.type)s"
    )
class DictUpdate( Validator ):

    def setParameters( self, **parameters ):
        self.parameters = parameters

    def on_value(self, context, value ):
        toUpdate = {}
        for (key,param) in self.parameters.items():
            if isinstance(param,ValidatorBase):
                param = param.validate( context, value )
            toUpdate[key] = param
        try:
            value.update( toUpdate )
        except Exception:
            raise Invalid( value, self, 'type' )

        return value

@messages\
    ( type = "Can not eliminate white spaces in values of type %(value.type)s"
    )
class EliminateWhiteSpace( Validator ):

    def on_value( self, context, value):
        try:
            return ''.join(value.split())
        except AttributeError:
            raise Invalid( value, self, 'type' )

# TODO: don't set context.value to None when in fact "" is given, see lib
@messages\
    ( type = "Can not strip white spaces in values of type %(value.type)s"
    )
class Strip( Validator ):

    def on_value( self, context, value):
        try:
            return value.strip()
        except AttributeError:
            raise Invalid( value, self, 'type' )

    on_blank = on_value

@messages\
    ( type = "Can not split values of type %(value.type)s"
    )
class Split( Validator ):

    def setParameters(self, separator=None, limit=-1):
        self.separator = separator
        self.limit = limit

    def on_value( self, context, value):
        try:
            return value.split( self.separator, self.limit )
        except Exception:
            raise Invalid( value, self, 'type' )

@messages\
    ( type = "Can not join values of type %(value.type)s"
    )
class Join( Validator):

    def setParameters(self, separator=''):
        self.separator = separator

    def on_value( self, context, value):
        try:
            return self.separator.join( value )
        except Exception:
            raise Invalid( value, self, 'type' )

@messages\
    ( type = "Can not encode %(value.type)s to %(format)s"
    , fail = "%(value)s cannot be encoded to %(format)s"
    )
class Encode( Validator ):

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

@messages\
    ( type = "Can not decode %(value.type)s to %(format)s"
    , fail = "%(value)s cannot be decoded to %(format)s"
    )
class Decode( Validator ):

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

@messages\
    ( type = "Unsupported type for insertion (%(value.type)s)"
    , fail = "Can not insert %(what)s at %(where)i"
    )
class Insert( Validator ):

    def setParameters( self, what, where=0 ):
        self.what = what
        self.where = where

    def on_value( self, context, value ):
        if ( isinstance( value, str ) and isinstance(value,str) )\
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
