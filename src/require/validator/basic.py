from .core import ValidatorFactory
from ..lib import messages

import logging
log = logging.getLogger(__name__)


class TypeValidator( ValidatorFactory ):
    converter = None

    def setParameters( self, data, convert=False ):
        data.convert = convert

    @property
    def convert( self ):
        if self.converter is None:
            self.converter = self.__class__( convert = True )

        return self.converter


class Dict( TypeValidator ):

    messages\
        ( type="Invalid type, must be a dictionary"
        , convert="Could not convert %s(inputType)s to dict"
        )

    def on_value(self, context, value):

        if not isinstance(value, dict):
            if  not context.data.convert:
                raise Invalid( 'type' )
            try:
                value = dict(value)
            except ValueError,TypeError:
                raise Invalid( 'convert', inputType=value.__class__.__name__ )

        if len( value ) == 0:
            return self.on_blank( context )

        return value


class List( TypeValidator ):

    messages\
        ( type="Invalid type, must be a list"
        , convert="Could not convert %(inputType)s to list"
        )

    def on_value(self, context, value):
        if isinstance(value,set) or isinstance(value,tuple):
            value = list(value)

        if not isinstance(value, list):
            if not context.data.convert:
                raise Invalid( 'type' )

            try:
                value = list(value)
            except ValueError,TypeError:
                raise Invalid( 'convert', inputType=value.__class__.__name__ )

        if len( value ) == 0:
            return self.on_blank( context )

        return value


class Boolean( TypeValidator):

    messages\
        ( type="Invalid type, must be a bool"
        )


    def on_value(self, context, value):
        if not (isinstance( value, bool ) or isinstance(value, int )):
            if self.convert:
                return bool(value)
            raise Invalid( 'type' )
        return value


class String( TypeValidator ):

    messages\
        ( type="Invalid type, must be a string"
        )

    def on_value(self, context, value):

        if isinstance( value, str):
            value = unicode(value)

        if not isinstance( value, unicode):
            if not self.convert:
                raise Invalid( 'type' )
            else:
                value = unicode(value)

        return value


class Integer( TypeValidator ):

    messages\
        ( type="Invalid type, must be an integer"
        , convert="Could not convert %(inputType)s to integer"
        )

    def on_value(self, context, value):
        if not isinstance( value, int ) and not isinstance( value, long):
            if not self.convert:
                raise Invalid( 'type' )
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise Invalid( 'convert', inputType=value.__class__.__name__ )

        return value

    @staticmethod
    def convert():
        return Integer( convert = True )


class Float( Integer ):
    messages\
        ( type="Invalid type, must be an integer"
        )

    def on_value(self, context, value):
        if not isinstance(value,float):
            if not self.convert:
                raise Invalid('type')
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise Invalid( 'convert',inputType=value.__class__.__name__ )

        return value

    @staticmethod
    def convert():
        return Float( convert = True )
