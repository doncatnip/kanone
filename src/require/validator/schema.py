from ..lib import pre_validate, missing, IGNORE, ValidationState, SchemaBase, ValidatorBase
from ..error import *
from .. import settings as s

from .core import Validator, Or, SchemaFailed, schema_failed, Not, Empty, Call
from .simple import List, Dict

import re, copy

convert_info = 'Will be converted to a dictionary'


class Schema( SchemaBase, Validator ):

    info = s.text.Schema.info
    msg = s.text.Schema.msg

    allow_extra_fields = False

    __validators__  = None
    __field_index__ = None


    def __prepare__( self, pre_validators, *validators ):

        if validators:
            self.__fields__ = validators

        pre_validators.insert\
            ( 0
            ,   ( Dict()\
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
                    raise Invalid( self.msg[0], field=key )
                break

            values[key] = valuelist[pos]

        context.value = values

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

    def on_validate(self, context, values):

        if not self.allow_extra_fields:

            field_index = self.field_index_get( context )
            for (key, value) in values.iteritems():
                if not key in field_index:
                    raise Invalid( self.msg[1], field=key )

        return self.vstate_get(context, values)


class ForEach( SchemaBase, Validator ):

    info = "Every item must met the criteria"

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

        context.value = retval

        return retval

    def field_index_get( self, context ):
        objstate = context.objstate(self)

        if context.value not in [missing, None]:
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

    def on_validate(self, context, value):

        field_index = self.field_index_get( context )

        values = dict(value)

        for key in field_index:
            elem = values.pop(key, missing)
            if elem is missing:
                raise Invalid( "Invalid item positions, please use 0,1,2,...", positions = values.keys() )

            elemcontext = context.new(key, elem)
            self.validator.do_validate( elemcontext, elem )

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

    def on_validate(self, context, value=IGNORE):

        field = missing
        try:
            field = context.require( self.field )
        except (IsMissing, DepencyError):
            pass

        if self.validator:
            fieldcontext = copy.copy( context.require(self.field, context_only=True) )
            fieldcontext.error = None

            result = self.validator(fieldcontext, value=field, cascade=False)

            if isinstance( result, ValidationState ):
                context.state.abort = True
                try:
                    result.__cascade__( errback = schema_failed )
                except SchemaFailed:
                    raise Invalid ( self.msg[1] )
                finally:
                    context.state.abort = False

            if fieldcontext.error:
                raise Invalid( fieldcontext.error[0]['msg'] )
        else:
            result = field

        if self.__copy__:
            return result

        return value

    def copy(self):
        self.__copy__ = True
        return self

    on_blank = on_missing = on_validate
