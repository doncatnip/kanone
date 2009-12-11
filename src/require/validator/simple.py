from ..lib import pre_validate, missing, IGNORE, SchemaBase, ValidatorBase
from ..error import *
from .. import settings as s

from .core import Validator

import logging
log = logging.getLogger(__name__)

class Dict(Validator):

    info = s.text.Dict.info
    msg = s.text.Dict.msg

    def on_value(self, context, value):

        if not isinstance(value, dict):
            raise Invalid(self.msg)

        if len( value ) == 0:
            return self.on_blank( context )

        return value

class List(Validator):

    info = s.text.List.info
    msg = s.text.List.msg

    def on_value(self, context, value):

        if isinstance(value, str) or not isinstance(value, list) and not isinstance(value, tuple):
            raise Invalid( self.msg )


        if len( value ) == 0:
            return self.on_blank( context )

        return value


class Boolean(Validator):

    info = s.text.Boolean.info

    def on_value(self, context, value):
        return bool(value)

class String(Validator):

    info = s.text.String.info
    msg  = s.text.String.msg

    def __init__(self, len_min=None, len_max=None, strip=False, transform=False):
        self.len_min = len_min
        self.len_max = len_max
        self.__strip__      = strip
        self.__transform__  = transform

    def __extra__(self, context):
        extra = { }
        if self.len_min is not None:
            extra["len_min"] = self.len_min
        if self.len_max is not None:
            extra["len_max"] = self.len_max
        return extra

    def __info__(self, context):
        extra = self.__extra__( context )
        if 'len_min' in extra:
            if 'len_max' in extra:
                return self.info[3]
            return self.info[1]
        if 'len_max' in extra:
            return self.info[2]
        return self.info[0]

    def on_value(self, context, value):

        log.debug( value )
        if self.__transform__:
            value = unicode(value)
        elif not isinstance( value, str) and not isinstance( value, unicode ):
            raise Invalid( self.msg[0] )
        if  ( self.len_min is not None and len(value)<self.len_min ):
            raise Invalid( self.msg[1] )
        elif  ( self.len_max is not None and len(value)>self.len_max ):
            raise Invalid( self.msg[2] )
        if self.__strip__:
            return value.strip()

        return value

    def strip(self):
        self.__strip__ = True
        return self

    def transform( self):
        self.__transform__ = True
        return self

class Integer(Validator):

    info = s.text.Integer.info
    msg  = s.text.Integer.msg

    def __init__(self, min=None, max=None):
        self.min = min
        self.max = max

    def __extra__(self, context):
        extra = {}
        if self.min is not None:
            extra["min"] = self.min
        if self.max is not None:
            extra["max"] = self.max
        return extra

    def __info__(self, context):
        extra = self.__extra__(context)
        if 'min' in extra:
            if 'max' in extra:
                return self.info[3]
            return self.info[1]
        if 'max' in extra:
            return self.info[2]
        return self.info[0]

    def on_value(self, context, value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise Invalid( self.msg[0] )

        if (self.min is not None and value<self.min):
            raise Invalid( self.msg[1] )
        elif (self.max is not None and value>self.max):
            raise Invalid( self.msg[1] )

        return value
