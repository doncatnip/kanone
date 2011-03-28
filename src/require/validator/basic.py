from .core import Validator
from ..lib import messages
from ..error import Invalid

import logging
log = logging.getLogger(__name__)

class TypeValidator( Validator ):
    __ignoreClassParameters__ = 'convert'

    converter = None

    def setParameters( self, convert=False ):
        self._convert = convert

    @classmethod
    def convert( klass ):
        if not klass.converter:
            klass.converter = klass( convert = True )
        return klass.converter


class Dict( TypeValidator ):

    messages\
        ( type="Invalid type (%(type)s), must be a dictionary"
        , convert="Could not convert %s(type)s to dict"
        )

    def on_value(self, context, value):

        if not isinstance(value, dict):
            if  not self._convert:
                raise Invalid( self, 'type' )
            try:
                value = dict(value)
            except (ValueError,TypeError):
                raise Invalid( self,'convert')

        if len( value ) == 0:
            return self.on_blank( context )

        return value


class List( TypeValidator ):

    messages\
        ( type="Invalid type (%(type)s), must be a list"
        , convert="Could not convert %(type)s to list"
        )

    def on_value(self, context, value):
        if isinstance(value,set) or isinstance(value,tuple):
            value = list(value)

        if not isinstance(value, list):
            if not self._convert:
                raise Invalid( self,'type' )

            try:
                value = list(value)
            except (ValueError,TypeError):
                raise Invalid( self,'convert' )

        if len( value ) == 0:
            return self.on_blank( context )

        return value


class Boolean( TypeValidator):

    messages\
        ( type="Invalid type (%(type)s), must be a bool"
        )

    def on_value(self, context, value):
        if isinstance(value, int )\
        and not(value<0 or value>1):
            value = bool(value)

        if not (isinstance( value, bool )):
            if self._convert:
                return bool(value)
            raise Invalid( self, 'type' )
        return value


class String( TypeValidator ):

    messages\
        ( type="Invalid type (%(type)s), must be a string"
        )

    def on_value(self, context, value):

        if isinstance( value, str):
            value = unicode(value)

        if not isinstance( value, unicode):
            if not self._convert:
                raise Invalid( self,'type' )
            else:
                value = unicode(value)

        return value


class Integer( TypeValidator ):

    messages\
        ( type="Invalid type (%(type)s), must be a integer"
        , convert="Could not convert %(type)s to integer"
        )

    def on_value(self, context, value):
        if not isinstance( value, int ) and not isinstance( value, long):
            if not self._convert:
                raise Invalid( self,'type' )
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise Invalid( self,'convert' )

        return value


class Float( TypeValidator ):
    messages\
        ( type="Invalid type (%(type)s), must be a floating point number"
        , convert="Could not convert %(type)s to a floating point number"
        )

    def on_value(self, context, value):
        if not isinstance(value,float):
            if not self._convert:
                raise Invalid( self,'type')
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise Invalid( self,'convert' )

        return value
