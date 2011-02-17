from ..lib import MISSING, PASS, messages, ValidatorBase
from ..error import Invalid

from .core import Validator
from .check import Match

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

        self.allowExtraFields = kwargs.get('allowExtraFields',False)
        self.returnList = kwargs.get('returnList',True)
        self.populateFirst = kwargs.get('populateFirst',None)

        self.__autopopulate__()

    # autopopulate:
    # Search for Field validators - if its used as or by any sub
    # validator, we need to populate the context before validating it
    # otherwise there will be no validator/value set yet when the
    # accessed field comes after the one which uses the Field validator.
    # We check this, because it saves performance if we only use it
    # when it's needed ( as one should allways instantiate his Schemas
    # only once per app ).
    def __autopopulate__(self):
        if self.populateFirst is None:
            self.populateFirst = False
            subValidators = []
            self.appendSubValidators( subValidators )

            for validator in subValidators:
                if isinstance(validator, FieldValidator ):
                    self.populateFirst = True
                    break

    # overridden (Validator)
    def appendSubValidators( self, subValidators ):
        self.field_index_get()
        for (key, validator) in self.__validators__:
            validator.appendSubValidators( subValidators )
            subValidators.append(validator)

    # overridden (Validator)
    def on_value( self, context, value ):
        extraFields = []

        field_index = list(self.field_index_get( context ))

        errors = []

        # we could also just fetch dict.values() later, but it would
        # just eat performance where it could be avoided
        if not self.returnList:
            result = {}
        else:
            result = []

        # create new child contexts, set values/validators and validate
        # ( if possible) while converting in one go to save performance
        if isinstance(value, list) or isinstance(value,tuple) or isinstance(value,set):
            valuelist = value
            value = {}

            for pos in range(len(valuelist)):
                try:
                    key = field_index[pos]
                except IndexError, e:
                    if not self.allowExtraFields:
                        extraFields.append( key )
                elif not extraFields:
                    contextChild = self.__newContext__( context, key, valuelist[pos] )
                    del field_index[pos]
                    if not self.populateFirst:
                        self.__validateField__( contextChild, result, errors )

        elif isinstance( value, dict ):
            for (key,val) in value:
                if not key in field_index:
                    if not self.allowExtraFields:
                        extraFields.append( key )
                elif not extraFields:
                    contextChild = self.__newContext__( context, key, val )
                    del field_index[field_index.index(key)]
                    if not self.populateFirst:
                        self.__validateField__( contextChild, result, errors )
        else:
            raise Invalid( 'type' )

        # maybe TODO: should we delete all created childs if there was an error ?
        if extraFields:
            raise Invalid( 'extraFields',extraFields=extraFields)

        # fill missing fields
        for key in field_index:
            contextChild = self.__newContext__( context, key, MISSING )
            if not self.populateFirst:
                self.__validateField__( contextChild, result, errors )

        if self.populateFirst:
            # validate all fields
            for key in self.__field_index__:
                self.__validateField__( context.childs[ key ], result, errors )

        if errors:
            raise Invalid( errors=errors)

        return result

    def __newContext__( self, context, key, value ):
        return context(value,self.validator_get( context, key ))

    def __validateField__( self, context, result, errors):
        try:
            result = context.result
        except Invalid,e:
            errors.append(e)
        if not self.returnList:
            result[key] = result
        else:
            result.append( result )

    def field_index_get( self, context ):
        if self.__field_index__ is none:
            if not hasattr(self, '__fieldset__'):
                raise SyntaxError('No fields defined in this schema: %s' % self.__class__.__name__)

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

    def __init__( self, criteria, onFirst=criteriaOnFirst, onLast=criteriaOnLast, numericKeys=True, returnList=True, populateFirst=None):

        if not isinstance( criteria, ValidatorBase ):
            criteria = Match( criteria )

        self.returnList = returnList
        self.numericKeys = numericKeys
        self.validator = criteria
        self.populateFirst = populateFirst
        self.__autopopulate__()

    def appendSubValidators( self, subValidators ):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def on_value( self, context, value ):
        typeError = False

        if self.returnList:
            result = []
        else:
            result = {}

        errors = []

        keyErrors = []

        keys = []

        if isinstance( value, list) or isinstance(value, tuple) or isinstance(value, set):
            for pos in range(len(value)):
                pos = str(pos)
                contextChild = self.__newContext__( context, pos, value[pos] )
                if not self.populateFirst:
                    self.__validateField__( contextChild, result, errors )
                else:
                    keys.append( pos )

        elif isinstance( value, dict):
            pos=0
            for (key, val) in value:
                if self.numericKeys:
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

                contextChild = self.__newContext__( context, key, val)
                if not self.populateFirst:
                    self.__validateField__( contextChild, result, errors )
                else:
                    keys.append( key )
        else:
            raise Invalid('type')

        if keyErrors:
            raise Invalid('numericKeys', keys=keyErrors)

        if self.populateFirst:
            for key in keys:
                self.__validateField__( context.childs[ key ], result, errors )

        if errors:
            raise Invalid(errors=errors)

        if not returnDict:
            return result.values()

        return result

    # overridden (Schema)
    def validator_get( self, context, key):
        return self.validator


class FieldValidator( Validator ):

    def __init__(self):
        raise SyntaxError( "FieldValidator cannot be used directly"

    def getField( self, context, path):
        pathSplit = path.split('.')

        if pathSplit[0] is not '':
            fieldcontext = self.root
        else:
            fieldcontext = self

            while pathSplit and pathSplit[0] is '':
                fieldcontext = fieldcontext.parent
                del pathSplit[0]

        if fieldcontext is self:
            selfReference = True

        if not selfReference:
            for part in pathSplit:
                if (fieldcontext.parent is self.parent) and (part == self.key):
                    selfReference = True
                    break
                fieldcontext = fieldcontext( part )

        if selfReference:
            raise SyntaxError( "Cannot reference myself. Nice try, though :)"

        return fieldcontext


class Field( FieldValidator ):

    messages\
        ( noResult='Field %(path)s has no result'
        )

    def __init__(self, path, criteria=None, useResult=False, copy=False):
        self.path = path
        self.copy = copy

        if criteria is None:
            self.copy = True
        elif not isinstance( criteria, Validator):
            criteria = Match( criteria )

        self.validator  = criteria

    def appendSubValidators( self, subValidators ):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def validate(self, context, value):

        fieldcontext = self.getField( self, context, self.path )

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

        if self.copy:
            return result

        return PASS
