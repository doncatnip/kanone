from .core import Validator, validator2parameter, messages

from ..error import Invalid

from datetime import date, datetime

import logging, sys
log = logging.getLogger(__name__)

_python3 = sys.version_info[0]>=3

class TypeValidator( Validator ):
    __ignoreClassParameters__ = 'convert'

    converter = None

    def setParameters( self, convert=False ):
        self._convert = convert

    @classmethod
    def convert( cls, *args, **kwargs ):
        if not cls.converter:
            kwargs['convert'] = True
            cls.converter = cls( *args, **kwargs )
        return cls.converter

@messages\
    ( type="Invalid type (%(value.type)s), must be a dictionary"
    , convert="Could not convert %s(type)s to dict"
    )
class Dict( TypeValidator ):

    def on_value(self, context, value):

        if not isinstance(value, dict):
            if  not self._convert:
                raise Invalid( value, self, 'type' )
            try:
                value = dict(value)
            except (ValueError,TypeError):
                raise Invalid( value, self,'convert')

        if len( value ) == 0:
            return self.on_blank( context, value )

        return value

@messages\
    ( type="Invalid type (%(value.type)s), must be a list"
    , convert="Could not convert %(value.type)s to list"
    )
class List( TypeValidator ):

    def on_value(self, context, value):
        if isinstance(value,set) or isinstance(value,tuple):
            value = list(value)

        if not isinstance(value, list):
            if not self._convert:
                raise Invalid( value, self,'type' )

            try:
                value = list(value)
            except (ValueError,TypeError):
                raise Invalid( value, self,'convert' )

        if len( value ) == 0:
            return self.on_blank( context, value )

        return value

@messages\
    ( type="Invalid type (%(value.type)s), must be a bool"
    , convert="Could not convert %(value.type)s to bool"
    )
class Boolean( TypeValidator):

    def setParameters( self, convert=False ):
        TypeValidator.setParameters( self, convert )

    def on_value(self, context, value):
        if not (isinstance( value, bool )):
            if not self._convert:
                raise Invalid( value, self, 'type' )
            else:
                try:
                    value = str(value).lower()
                except Exception as e:
                    raise Invalid( value, self, 'convert' )
                if value in ('1', 'true', 'yes', 'on'):
                    value = True
                elif value in ('0', 'false', 'no', 'off'):
                    value = False
                else:
                    raise Invalid( value, self, 'convert' )
        return value

@messages\
    ( type="Invalid type (%(value.type)s), must be a string"
    , convert="Could not convert %(value.type)s to string"
    )
class String( TypeValidator ):

    def setParameters( self, convert=False ):
        TypeValidator.setParameters( self, convert )

    def on_value_py2( self, context, value ):
        if not isinstance( value, basestring):
            if not self._convert:
                raise Invalid( value, self, 'type' )
            else:
                try:
                    value = value.__str__()
                except AttributeError:
                    raise Invalid( value, self, 'convert' )

        return value

    def on_value(self, context, value):
        if not isinstance( value, str):
            if not self._convert:
                raise Invalid( value, self, 'type' )
            else:
                try:
                    value = value.__str__()
                except AttributeError:
                    raise Invalid( value, self, 'convert' )


        return value

if not _python3:
    String.on_value = String.on_value_py2

@messages\
    ( type="Invalid type (%(value.type)s), must be a integer"
    , convert="Could not convert %(value.type)s to integer"
    )
class Integer( TypeValidator ):

    def on_value(self, context, value):
        if not isinstance( value, int ) and not isinstance( value, int):
            if not self._convert:
                raise Invalid( value, self,'type' )
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise Invalid( value, self,'convert' )

        return value

@messages\
    ( type="Invalid type (%(value.type)s), must be a floating point number"
    , convert="Could not convert %(value.type)s to a floating point number"
    )
class Float( TypeValidator ):

    def on_value(self, context, value):
        if not isinstance(value,float):
            if not self._convert:
                raise Invalid( value, self,'type')
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise Invalid( value, self,'convert' )

        return value

@messages\
    ( type="Invalid type (%(value.type)s), must be a date"
    , convert='Could not convert "%(value)s"(%(value.type)s) to a date'
    )
class Date( Validator ):

    def setParameters( self, formatter="%Y-%m-%d", convert=False ):
        self._convert = convert
        validator2parameter(self, 'formatter', formatter)

    def on_value(self, context, value ):

        if not isinstance( value, date):
            if not self._convert:
                raise Invalid( value, self, 'type' )
            else:
                try:
                    return datetime.strptime( value, context.params.formatter ).date()
                except ValueError:
                    raise Invalid( value, self, 'convert' )
            
        return value

    @classmethod
    def convert( cls, formatter ):
        return cls( formatter=formatter, convert=True )


@messages\
    ( type="Invalid type (%(value.type)s), must be a datetime"
    , convert='Could not convert "%(value)s"(%(value.type)s) to a datetime'
    )
class DateTime( Validator ):

    def setParameters( self, formatter="%Y-%m-%d", convert=False ):
        self._convert = convert
        validator2parameter(self, 'formatter', formatter)

    def on_value(self, context, value ):

        if not isinstance( value, datetime):
            if not self._convert:
                raise Invalid( value, self, 'type' )
            else:
                try:
                    return datetime.strptime( value, context.params.formatter )
                except ValueError:
                    raise Invalid( value, self, 'convert' )
            
        return value

    @classmethod
    def convert( cls, formatter ):
        return cls( formatter=formatter, convert=True )
