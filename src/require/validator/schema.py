from ..lib import pre_validate, missing, IGNORE, ValidationState, SchemaBase, ValidatorBase
from ..error import *
from .. import settings as s

from .core import Validator, Or, SchemaFailed, schema_failed, Not, Empty, Call, Pass, Match
from .simple import List, Dict

import re, copy

import logging
log = logging.getLogger(__name__)

convert_info = 'Will be converted to a dictionary'


class Schema( SchemaBase, Validator ):

    info = s.text.Schema.info
    msg = s.text.Schema.msg

    allow_extra_fields = False

    __validators__  = None
    __field_index__ = None

    # TODO
    filled_min   = None
    filled_max   = None

    def __prepare__( self, pre_validators, *validators ):

        if validators:
            self.__fields__ = validators

        pre_validators.insert\
            ( 0
            ,   ( Dict()
                | ( List() & Call( self.list_convert ).text( info=convert_info ) )
                )
            )

        return pre_validators

    def list_convert( self, context, values ):

        valuelist = values
        values = {}

        field_index = self.field_index_get( context )

        for pos in range(len(valuelist)):
            try:
                key = field_index[pos]
            except IndexError,e:
                if not self.allow_extra_fields:
                    raise Invalid( self.msg[0] )
                break

            values[key] = valuelist[pos]

        return values

    def field_index_get( self, context ):

        if self.__field_index__ is None:

            if not hasattr(self, '__fields__'):
                raise TypeError('No fields defined in this schema: %s' % self.__class__.__name__)

            self.__validators__ = {}
            self.__field_index__ = []
            for (name,validator) in self.__fields__:
                self.__validators__[name] = validator
                self.__field_index__.append(name)

        return self.__field_index__

    def validator_get( self, context, key ):
        field_index = self.field_index_get( context )

        if key not in self.__validators__:
            raise AttributeError("No Validator for field '%s' set" % key)
        return self.__validators__[key]

    def __extra__(self, context):
        return {'fields' : self.field_index_get( context ) }

    def on_value( self, context, values ):

        field_index = self.field_index_get( context )
        for (key, value) in values.iteritems():
            if not key in field_index and not self.allow_extra_fields:
                raise Invalid( self.msg[1], field=key )

        return self.vstate_get(context, values)

class ForEach( SchemaBase, Validator ):

    info = "Every item must met the criteria"

    # TODO
    filled_min   = None
    filled_max   = None

    def __prepare__( self, pre_validators, criteria, numeric_keys=True):

        list_check = ( List() & Call( self.list_convert ).text( info=convert_info )  )
        pre_validators.insert(0, Dict() | list_check )

        if not isinstance( criteria, ValidatorBase ):
            criteria = Match( criteria )

        self.numeric_keys = numeric_keys
        self.validator = criteria

        return pre_validators

    def list_convert( self, context, values ):
        retval = {}

        for pos in range(len(values)):
            retval[str(pos)] = values[pos]

        return retval

    def field_index_get( self, context, value=missing ):
        objstate = context.objstate(self)
        if 'field_index' not in objstate:
            if value is missing:
                value = context.value

            if value not in [missing, None]:
                if not self.numeric_keys:
                    field_index = context.value.keys()
                else:
                    field_index = [ str(pos) for pos in range(len(context.value)) ]

                objstate.field_index = field_index

        return objstate.field_index

    def __extra__(self, context):
        retval = { 'numeric_keys': self.numeric_keys }
        if not self.numeric_keys:
            retval['fields'] = self.field_index_get( context )
        return retval

    def validator_get( self, context, key):
        return self.validator

    def on_value(self, context, value):

        field_index = self.field_index_get( context )

        values = dict(value)

        for key in field_index:
            elem = values.pop(key, missing)
            if elem is missing:
                raise Invalid( "Invalid item positions, please use 0,1,2,...", positions = values.keys() )

            elemcontext = context.new(key, elem)
            self.validator.__validate__( elemcontext, elem )

        if values:
            raise Invalid( "Invalid item positions, please use 0,1,2,...", positions = values.keys() )

        return self.vstate_get(context, value)

class Field( Validator ):

    info = s.text.Field.info
    msg = s.text.Field.msg

    __copy__ = False

    def __init__(self, field, criteria=None):
        self.field      = field

        if criteria is None:
            self.copy()

        elif  not isinstance( criteria, Validator):
            criteria = Match( criteria )

        self.validator  = criteria

    def __extra__(self, context):
        retval = { 'field': self.field }
        if self.validator is not None:
            retval['criteria'] = self.validator.info_get(context)
        return retval

    def __info__(self, context ):
        if self.validator is None:
            return Field.info[0]
        return Field.info[1]

    def validate(self, context, value):

        if self.field.startswith('(this).'):
            field = "%s%s%s" % \
                ( '.'.join(context.keypath[:-1])
                , [ '', '.' ][len(context.keypath)>1]
                , self.field[7:]
                )
        else:
            field = self.field

        fieldcontext = copy.copy( context.require(field, context_only=True) )
        fieldcontext.error = None

        if self.validator is not None:
            fieldvalue = getattr(fieldcontext, 'result', fieldcontext.value)

            result = self.validator.__validate__(fieldcontext, fieldvalue)

            if isinstance( result, ValidationState ):
                try:
                    result.__cascade__( errback = schema_failed )
                except SchemaFailed:
                    raise Invalid ( self.msg[1] )

            if fieldcontext.error:
                raise Invalid( fieldcontext.error[0]['msg'] )

            if self.__copy__:
                return result
        else:
            if (hasattr(fieldcontext,'result')):
                return fieldcontext.result

        return value

    def copy(self):
        self.__copy__ = True
        return self
