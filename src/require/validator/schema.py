from ..lib import MISSING, PASS, messages, ValidatorBase
from ..error import Invalid

from .core import Validator, Match

import re

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

    def __init__( self, *validators, **kwargs ):

        if validators:
            self.__fieldset__ = validators

        self.allow_extraFields = kwargs.get('allow_extraFields',False)

    def appendSubValidators( self, subValidators ):
        self.field_index_get()
        for (key, validator) in self.__validators__:
            validator.appendSubValidators( subValidators )
            subValidators.append(validator)

    def on_value( self, context, value ):
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
                except IndexError, e:
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
            self.__newContext__( context, result, errors, key, MISSING )

        if typeError:
            raise self.invalid( 'type' )
        elif extraFields:
            raise self.invalid( 'extraFields',extraFields=extraFields)
        elif errors:
            raise self.invalid( errors=errors)

        return result

    def __newContext__( self, context, result, errors, key, value ):
        fieldcontext = context(key)
        fieldcontext.validator = self.validator_get( context, str(key) )
        fieldcontext.value = value
        try:
            result[key] = fieldcontext.result
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
        ( keys='Invalid keys, please use 0,1,2,... (keys: %(keys)s)'
        )

    def __init__( self, criteria, returnDict=False):

        if not isinstance( criteria, ValidatorBase ):
            criteria = Match( criteria )

        self.numericKeys = numericKeys
        self.validator = criteria

    def appendSubValidators( self, subValidators ):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def on_value( self, context, value ):
        typeError = False
        result = {}
        errors = []

        keyErrors = []

        if isinstance( value, list) or isinstance(value, tuple) or isinstance(value, set):
            for pos in range(len(value)):
                self.__newContext__( context, result, errors, pos, value[pos] )

        elif isinstance( value, dict):
            pos=0
            for (key, val) in value:
                if not returnDict:
                    try:
                        key = int(key)
                    except ValueError,e:
                        keyErrors.append(key)
                        continue
                    else:
                        if key != pos:
                            keyErrors.append(key)
                            continue
                    finally:
                        pos+=1

                self.__newContext__( context, result, errors, key, val)
        else:
            typeError = True

        if typeError:
            raise self.invalid('type')
        elif keyErrors:
            raise self.invalid('numericKeysError', keys=keyErrors)
        elif errors:
            raise self.invalid(errors=errors)

        if not returnDict:
            return result.values()

        return result

    def validator_get( self, context, key):
        return self.validator


class Field( Validator ):

    messages\
        ( noResult='Field %(path)s has no result'
        )

    def __init__(self, path, criteria=None, useResult=False, copy=False, update=False):
        self.path = path
        self.copy = copy
        self.update = update

        if criteria is None:
            self.copy = True
        elif not isinstance( criteria, Validator):
            criteria = Match( criteria )

        self.validator  = criteria

    def appendSubValidators( self, subValidators ):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def validate(self, context, value):
        path = path.split('.')

        if path[0] is not '':
            fieldcontext = self.root
        else:
            fieldcontext = self

            while path and path[0] is '':
                fieldcontext = fieldcontext.parent
                del path[0]

        for part in path:
            fieldcontext = fieldcontext( part )

        result = MISSING

        if self.validator is not None:
            if useResult:
                value = fieldcontext.value
            else:
                try:
                    value = fieldcontext.result
                except Invalid,e:
                    value = PASS

            if value is not PASS:
                result = self.validator.validate( fieldcontext, value )

        if self.update and result not in [MISSING,PASS]:
            context['value'] = result

        if self.copy:
            return result

        return PASS
