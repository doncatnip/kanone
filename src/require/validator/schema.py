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
                if isinstance(validator, Field ):
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

        # allow access to childs of this context while validating
        context.isPopulated = True

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
                    childContext = self.__newContext__( context, key, valuelist[pos] )
                    del field_index[pos]
                    if not self.populateFirst:
                        self.__validateField__( childContext, result, errors )

        elif isinstance( value, dict ):
            for (key,val) in value:
                if not key in field_index:
                    if not self.allowExtraFields:
                        extraFields.append( key )
                elif not extraFields:
                    childContext = self.__newContext__( context, key, val )
                    del field_index[field_index.index(key)]
                    if not self.populateFirst:
                        self.__validateField__( childContext, result, errors )
        else:
            context.isPopulated = False
            raise Invalid( 'type' )

        # maybe TODO: should we delete all created childs if there was an error ?

        if extraFields:
            context.isPopulated = False
            raise Invalid( 'extraFields',extraFields=extraFields)

        # fill missing fields
        for key in field_index:
            childContext = self.__newContext__( context, key, MISSING )
            if not self.populateFirst:
                self.__validateField__( childContext, result, errors )

        if self.populateFirst:

            # validate all fields
            for key in self.__field_index__:
                self.__validateField__( context( key ), result, errors )


        context.isPopulated = False

        if errors:
            raise Invalid( errors=errors)

        return result

    def __newContext__( self, context, key, value ):
        return context(value,self.validator_get( context, str(key) ))

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
        ( keys='Invalid keys, please use 0,1,2,... (keys: %(keys)s)'
        )

    def __init__( self, criteria, numericKeys=True, returnList=True, populateFirst=None):

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
            raise Invalid('type')
        elif keyErrors:
            raise Invalid('keys', keys=keyErrors)
        elif errors:
            raise Invalid(errors=errors)

        if not returnDict:
            return result.values()

        return result

    # overridden (Schema)
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
