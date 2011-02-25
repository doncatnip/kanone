from ..lib import MISSING, messages, inherit
from ..error import Invalid

from .core import ValidatorBase, Validator
from .check import PASS, Match

import re

import logging
log = logging.getLogger(__name__)

class SchemaData:

    def __init__(self, validationFunc, indexFunc=None):
        self.validationFunc = validationFunc
        self.indexFunc = indexFunc
        self.values = None

class Schema( Validator ):

    inherit\
        ( 'validators'
        , 'keyIndexRelation'
        , 'index'
        )

    messages\
        ( fail='Validation failed (errors: %(errors)s )'
        , extraFields='No extra fields allowed (extra fields: %(extraFields)s)'
        , type='Invalid input type (must be dict, list or tuple)'
        )

    def setArguments( self, *_fieldset ):
        assert len(_fieldset)%2==0
        (self.validators,self.index,self.keyIndexRelation)\
            = self.getValidators( _fieldset or self.__fieldset__ )
        if not self.validators:
            raise SyntaxError('No fieldset given')

    def setParameters( self, allowExtraFields=False, returnList=False ):
        self.allowExtraFields = allowExtraFields
        self.returnList = returnList

    def appendSubValidators( self, subValidators ):
        for validator in self.validators.values():
            validator.appendSubValidators( subValidators )
            subValidators.append(validator)

    def validateField( self, context, schemaData ):
        try:
            context.validator = self.validators[ context.key ]
        except KeyError:
            raise SyntaxError("No validator set for %s" % context.path)

        key = schemaData.isList\
            and self.keyIndexRelation[ key ] or context.key

        context.value = schemaData.values.get\
            ( key
            , MISSING
            )

        return context.validator.validate( context, context.value )

    def getKeyByIndex( self, index, schemaData ):
        return self.index[ index ]

    def on_value( self, context, value ):
        data = SchemaData( validateField, getKeyByIndex )
        data.isList = isinstance(value, list) or isinstance(value,tuple) or isinstance(value,set)
        if not data.isList and not isinstance( value, dict ):
            raise Invalid('type')

        if not self.allowExtraFields:
            extraFields = data.isList\
                and len(value) or value.keys()

        errors = []

        data.values = value
        context.setSchemaData( data )
        result = {}

        for pos in range(len(self.index)):
            key = self.index[pos]
            try:
                result[ key ] = context( pos ).result
            except Invalid,e:
                errors.append( e )
            if not self.allowExtraFields:
                if data.isList:
                    extraFields-=1
                else:
                    del extraFields[ key ]

        context.resetSchemaData()

        if extraFields:
            raise Invalid('extraFields',extraFields=extraFields)

        if errors:
            raise Invalid(errors = errors )

        if self.returnList:
            return result.values()

        return result


    @classmethod
    def getValidators( klass, _fieldset  ):
        if not _fieldset:
            return None

        validators = {}
        keyIndexRelation = {}
        index = []

        pos = 0
        for (name,validator) in _fieldset:
            validators[name] = validator
            keyIndexRelation[ name ] = pos
            index.append( name )
            pos += 1

        return (validators,index,keyIndexRelation)


class ForEach( Validator ):

    messages\
        ( numericKeys='Invalid keys, please use 0,1,2,... (keys: %(keys)s)'
        , type='Invalid input type (must be dict, list or tuple)'
        )

    def setParameters( self, criteria, numericKeys=True, returnList=True ):

        if not isinstance( criteria, ValidatorBase ):
            criteria = Match( criteria )

        self.returnList = returnList
        self.numericKeys = numericKeys
        self.validator = criteria

    def appendSubValidators( self, subValidators ):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def validateItem( self, context, schemaData ):
        print "validateItem %s" % context.value
        key = schemaData.isList\
            and int(context.key) or context.key

        context.value = schemaData.values[ key ]
        context.validator = self.validator

        return context.validator.validate( context, context.value )

    def getKeyByIndex( self, index, schemaData ):
        print "getKeyByIndex %s" % index
        return str( index )

    def on_value( self, context, value ):

        data = SchemaData( self.validateItem )
        data.isList = isinstance( value, list) or isinstance(value, tuple) or isinstance(value, set)

        if not data.isList:
            if not isinstance(data, dict ):
                raise Invalid( 'type' )

        result = {}
        errors = []

        data.values = value
        context.setSchemaData( data )

        if self.isList or self.numericKeys:
            data.indexFunc = self.getKeyByIndex

            for pos in range( len( value ) ):
                resultKey = str(pos)
                if not self.isList:
                    contextKey = value.get(resultKey,None) and pos
                    if contextKey is None:
                        context.resetSchemaData()
                        raise Invalid('numericKeys',keys=data.keys())
                else:
                    contextKey = pos

                try:
                    result[ resultKey ] = context( contextKey ).result
                except Invalid, e:
                    errors.append( e )
        else:
            for key in value.keys():
                try:
                    result[ key ] = context( key ).result
                except Invalid, e:
                    errors.append( e )

        context.resetSchemaData()

        if errors:
            raise Invalid(errors=errors)

        if self.returnList:
            return result.values()

        return result


class FieldValidator( Validator ):

    def setParameters(self):
        raise SyntaxError( "FieldValidator cannot be used directly" )

    def getField( self, context, path):
        pathSplit = path.split('.')

        if pathSplit[0] is not '':
            fieldcontext = self.root
        else:
            fieldcontext = self

            while pathSplit and pathSplit[0] is '':
                fieldcontext = fieldcontext.parent
                del pathSplit[0]

        for part in pathSplit:
            if part.startswith('(') and part.endswith(')'):
                part = int(part[1:-1])
            fieldcontext = fieldcontext( part )

        if fieldcontext is context:
            raise SyntaxError( "Cannot reference myself. Nice try, though :)" )

        return fieldcontext


class Field( FieldValidator ):

    messages\
        ( noResult='Field %(path)s has no result'
        )

    def setParameters(self, path, criteria=None, useResult=False, copy=False):
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
            targetValue = PASS

            if not useResult:
                targetValue = fieldcontext.value
            else:
                try:
                    targetValue = fieldcontext.result
                except Invalid,e:
                    targetValue = PASS

            if targetValue is not PASS:
                result = self.validator.validate( fieldcontext, targetValue )

        if self.copy:
            return result

        return value
