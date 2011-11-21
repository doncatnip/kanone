from .core import Validator, validator2parameter

from ..lib import messages
from ..error import Invalid

from datetime import datetime

import logging
log = logging.getLogger(__name__)

class TypeValidator( Validator ):
    __ignoreClassParameters__ = 'convert'

    converter = None

    def setParameters( self, convert=False ):
        self._convert = convert

    @classmethod
    def convert( klass, *args, **kwargs ):
        if not klass.converter:
            kwargs['convert'] = True
            klass.converter = klass( *args, **kwargs )
        return klass.converter


class Dict( TypeValidator ):

    messages\
        ( type="Invalid type (%(value.type)s), must be a dictionary"
        , convert="Could not convert %s(type)s to dict"
        )

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


class List( TypeValidator ):

    messages\
        ( type="Invalid type (%(value.type)s), must be a list"
        , convert="Could not convert %(value.type)s to list"
        )

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


class Boolean( TypeValidator):

    messages\
        ( type="Invalid type (%(value.type)s), must be a bool"
        )

    def on_value(self, context, value):
        if isinstance(value, int )\
        and not(value<0 or value>1):
            value = bool(value)

        if not (isinstance( value, bool )):
            if self._convert:
                return bool(value)
            raise Invalid( value, self, 'type' )
        return value


class String( TypeValidator ):

    messages\
        ( type="Invalid type (%(value.type)s), must be a string"
        , encoding='Could not decode "%(value)s" to %(encoding)s'
        )

    def setParameters( self, convert=False, encoding='utf-8' ):
        TypeValidator.setParameters( self, convert )
        validator2parameter( self, 'encoding', encoding )

    def on_value(self, context, value):
        if isinstance( value, str):
            encoding = context.params.encoding
            try:
                value = value.decode( encoding )
            except UnicodeDecodeError:
                raise Invalid( value, self, 'encoding', encoding=encoding )

        elif not isinstance( value, unicode):
            encoding = context.params.encoding
            if not self._convert:
                raise Invalid( value, self,'type', encoding=encoding )
            else:
                try:
                    value = str(value).decode( encoding )
                except UnicodeDecodeError:
                    raise Invalid( value, self,'encoding', encoding=encoding )

        return value


class Integer( TypeValidator ):

    messages\
        ( type="Invalid type (%(value.type)s), must be a integer"
        , convert="Could not convert %(value.type)s to integer"
        )

    def on_value(self, context, value):
        if not isinstance( value, int ) and not isinstance( value, long):
            if not self._convert:
                raise Invalid( value, self,'type' )
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise Invalid( value, self,'convert' )

        return value


class Float( TypeValidator ):
    messages\
        ( type="Invalid type (%(value.type)s), must be a floating point number"
        , convert="Could not convert %(value.type)s to a floating point number"
        )

    def on_value(self, context, value):
        if not isinstance(value,float):
            if not self._convert:
                raise Invalid( value, self,'type')
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise Invalid( value, self,'convert' )

        return value


class DateTime( Validator ):

    messages\
        ( type="Invalid type (%(value.type)s), must be a datetime"
        , convert='Could not convert "%(value)s"(%(value.type)s) to a datetime'
        )

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
    def convert( klass, formatter ):
        return klass( formatter=formatter, convert=True )
