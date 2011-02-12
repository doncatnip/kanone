from ..lib import MISSING, IGNORE, ValidatorBase
from ..error import Invalid
from .. import settings as s

from .core import Validator, Or, SchemaFailed, schema_failed, Not, Empty, Call, Pass, Match
from .simple import List, Dict

import re, copy

import logging
log = logging.getLogger(__name__)


class Schema( Validator ):

    messages\
        ( fail='Validation failed (errors: %(errors)s )'
        , extraFields='No extra fields allowed (extra fields: %(extraFields)s)'
        , type='Invalid input type (must be dict, list or tuple)'
        )

    __validators__  = None
    __field_index__ = None

    def __init__( self, *validators, allow_extraFields=False ):

        if validators:
            self.__fieldset__ = validators

        self.allow_extraFields = False


    def populate( self, context, value ):
        if value in [None, MISSING]:
            return value

        extraFields = []

        typeError = False
        errors = []
        result = {}

        field_index = list(self.field_index_get( context ))

        if isinstance(value, list) or isinstance(value,tuple) or isinstance(value,set):
            valuelist = value
            value = {}

            for pos in range(len(valuelist)):
                try:
                    key = field_index[pos]
                except IndexError,e:
                    if not self.allow_extraFields:
                        extraFields.append( key )
                else:
                    self.__newContext__( context, result, errors, key, valuelist[pos] )
                    del field_index[pos]

        elif isinstance( value, dict ):
            for (key,val) in value:
                if not key in field_index:
                    extraFields.append( key )
                else:
                    self.__newContext__( context, result, errors, key, val )
                    del field_index[field_index.index(key)]
        else:
            typeError = True

        # fill missing fields
        for key in field_index:
            self.__newContext__( context, result, errors, key, value )

        if typeError:
            context.data( self ).error = self.invalid( 'type' )
        elif extraFields:
            context.data( self ).error = self.invalid( 'extraFields',extraFields=extraFields)
        elif errors:
            context.data( self ).error = self.invalid( 'fail',errors=errors)

        context.data( self ).result = result

        return value

    def on_value(self, context, value):
        if context.data( self ).error:
            raise context.data( self ).error
        return context.data( self ).result

    def __newContext__( self, context, result, errors, key, value ):
        fieldcontext = context(key)
        fieldcontext.validator = self.validator_get( context, str(key) )
        values[key] = fieldcontext.value = value
        try:
            result[key] = fieldcontext.validate()
        except Invalid,e:
            errors.append( e )


    def field_index_get( self, context ):
        if self.__field_index__ is none:
            if not hasattr(self, '__fieldset__'):
                raise TypeError('No fields defined in this schema: %s' % self.__class__.__name__)

            self.__validators__ = {}
            self.__field_index__ = []
            for (name,validator) in self.__fieldset__:
                self.__validators__[name] = validator
                self.__field_index__.append(name)

        return self.__field_index__

    def validator_get( self, context, key ):
        field_index = self.field_index_get( context )

        if key not in self.__validators__:
            raise AttributeError("No Validator for field '%s' set" % context.path)
        return self.__validators__[key]



class ForEach( Schema ):

    messages\
        ( numericKeys='Invalid keys, please use 0,1,2,... (keys: %(keys)s)'
        )

    def __init__( self, criteria, numericKeys=True):

        if not isinstance( criteria, ValidatorBase ):
            criteria = Match( criteria )

        self.numericKeys = numericKeys
        self.validator = criteria

    def populate( self, context, value ):
        typeError = False
        result = {}
        errors = []

        numericKeysError = []

        if isinstance( value, list) or isinstance(value, tuple) or isinstance(value, set):
            for pos in range(len(value)):
                self.__newContext__( context, result, errors, pos, value[pos] )

        elif isinstance( value, dict):
            pos=0
            for (key, val) in value:
                if self.numericKeys:
                    try:
                        key = int(key)
                    except ValueError,e:
                        numericKeysError.append(key)
                    else:
                        if key != pos:
                            numericKeysError.append(key)
                    finally:
                        pos+=1

                self.__newContext__( context, result, errors, key, val)
        else:
            typeError = True

        if typeError:
            context.data( self ).error = self.invalid('type')
        elif numericKeysError:
            context.data( self ).error = self.invalid('numericKeysError', keys=numericKeysError)
        elif errors:
            context.data( self ).error = self.invalid('fail', errors=errors)

        if result:
            context.data( self ).result = result

        return value

    def validator_get( self, context, key):
        return self.validator


class Field( Validator ):

    messages\
        ( notFound='Field %(path)s not found'
        )

    def __init__(self, path, criteria=None, copy=False):
        self.path = path

        self.copy = copy

        if criteria is None:
            self.copy = True
        elif not isinstance( criteria, Validator):
            criteria = Match( criteria )
        if criteria is not None:
            self.__update__ = criteria.__update__

        self.validator  = criteria

    def populate(self, context, value):
        
        if self.field.startswith('(root).'):
            path = self.field[7:]
            parent = self.root
        else:
            path = self.path.split('.')
            parent = self


            parent = self.parent

        if self.validator is not None:
            return self.validator.populate( fieldcontext, value )
        return value

    def validate(self, context, value):

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
