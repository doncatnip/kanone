# -*- coding: utf-8 -*-

from ..lib import PASS, MISSING, messages, inherit
from ..error import Invalid

from .core import ValidatorBase, Validator
from .check import Match

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
        ( fail=None
        , extraFields='No extra fields allowed (extra fields: %(extraFields)s)'
        , type='Invalid input type (%(value.type)s) - must be dict, list or tuple.'
        )

    def setArguments( self, *_fieldset ):
        if not hasattr(self,'__fieldset__') and ((len(_fieldset)%2 != 0) or (len(_fieldset)<2)):
            raise SyntaxError("Invalid number of fields supplied (%s). Use: %s(key, value, key, value, …)" % (len(_fieldset),self.__class__.__name__))

        fieldpairs = []
        pos = 0
        for value in _fieldset:
            if pos%2 != 0:
                fieldpairs.append((name,value))
            else:
                name = value
            pos += 1

        (self.validators,self.index,self.keyIndexRelation)\
            = self.getValidators( fieldpairs or self.__fieldset__ )

        if not self.validators:
            raise SyntaxError('No fieldset given')

    def setParameters\
        ( self
        , allowExtraFields=False
        , returnList=False
        , createContextChilds=True
        ):

        self.returnList = returnList

        self.allowExtraFields = allowExtraFields
        self.on_value = createContextChilds\
            and self._createContextChilds_on_value\
            or self._on_value



    def appendSubValidators( self, subValidators ):
        for validator in self.validators.values():
            validator.appendSubValidators( subValidators )
            subValidators.append(validator)

    def validateField( self, context, schemaData ):
        try:
            context.validator = self.validators[ context.key ]
        except KeyError:
            raise SyntaxError("No validator set for %s" % context.path)

        if schemaData.isList:
            try:
                value = schemaData.values[ self.keyIndexRelation[ context.key ] ]
            except IndexError:
                value = MISSING
        else:
            value = schemaData.values.get\
                ( context.key
                , MISSING
                )

        context.__value__ = value
        return context.validator.validate( context, value )

    def _on_value( self, context, value ):
        isList = isinstance(value, list) or isinstance(value,tuple) or isinstance(value,set)
        if not isList and not isinstance( value, dict ):
            raise Invalid( value, self, 'type')

        extraFields = None
        if not self.allowExtraFields:
            if isList:
                extraFields = max( len(value), len(self.index) )
            else:
                extraFields = value.keys()

        if self.returnList:
            result = []
        else:
            result = {}

        numValues = len(value)

        for pos in range(len(self.index)):
            key = self.index[pos]
            if isList is True:
                if numValues>pos:
                    val = value[ pos ]
                    if not self.allowExtraFields:
                        extraFields-=1
                else:
                    val = MISSING
            else:
                val = value.get( key, MISSING)
                if not self.allowExtraFields and val is not MISSING:
                    try: extraFields.remove(key)
                    except: pass

            res = self.validators[ key ].validate( context, val )
            if self.returnList:
                result.append( res )
            else:
                result[ key ] = res

            pos += 1

        if extraFields:
            raise Invalid( value, self, 'extraFields',extraFields=extraFields)

        return result


    def _createContextChilds_on_value( self, context, value ):
        data = SchemaData( self.validateField, lambda index, schemaData: self.index[index] )
        data.isList = isinstance(value, list) or isinstance(value,tuple) or isinstance(value,set)
        if not data.isList and not isinstance( value, dict ):
            raise Invalid( value, self, 'type')

        extraFields = None
        if not self.allowExtraFields:
            if data.isList:
                extraFields = max( len(value), len(self.index) )
            else:
                extraFields = value.keys()

        errors = []

        data.values = value
        context.setSchemaData( data )

        if self.returnList:
            result = []
        else:
            result = {}

        for pos in range(len(self.index)):
            key = self.index[pos]
            try:
                res = context( pos ).result
            except Invalid as e:
                errors.append( e.context.key )
            else:
                if self.returnList:
                    result.append( res )
                else:
                    result[ key ] = res

            if not self.allowExtraFields:
                if data.isList:
                    extraFields-=1
                else:
                    try: extraFields.remove(key)
                    except: pass

        context.resetSchemaData()

        if extraFields:
            raise Invalid( value, self, 'extraFields',extraFields=extraFields)

        if errors:
            raise Invalid( value, self, errors=errors )

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
        ( fail=None
        , numericKeys='Invalid keys, please use 0,1,2,... (keys: %(keys)s)'
        , type='Invalid input type (%(value.type)s) - must be dict, list, tuple or set'
        , listType='Invalid input type (must be list, tuple or set)'
        )

    def setParameters\
        ( self
        , criteria
        , numericKeys=True
        , returnList=True
        , createContextChilds=True ):

        if not isinstance( criteria, ValidatorBase ):
            criteria = Match( criteria )

        self.returnList = returnList
        self.numericKeys = numericKeys
        self.validator = criteria
        self.validate = createContextChilds and self._createContextChilds_on_value \
            or self._on_value

    def appendSubValidators( self, subValidators ):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def validateItem( self, context, schemaData ):
        if schemaData.isList:
            key = int(context.key)
        else:
            key = context.key

        context.validator = self.validator
        value = schemaData.values[ key ]
        context.__value__ = value
        return context.validator.validate( context, value )

    def _on_value( self, context, value ):
        if self.returnList:
            result = []
        else:
            result = {}

        isList = isinstance( value, list) or isinstance(value, tuple) or isinstance(value, set)

        if isList or self.numericKeys:
            for pos in range( len( value ) ):
                if isList is False:
                    val = value.get(str(pos),MISSING)
                    if val is MISSING:
                        raise Invalid( value, self, 'numericKeys', keys=value.keys() )
                else:
                    val = value[pos]

                #try:
                res = self.validator.validate( context, val )
                #except Invalid as e:
                #    e.value = val
                #    raise e

                if self.returnList is True:
                    result.append( res )
                else:
                    result[pos] = res
        else:
            for (key, val) in value.iteritems():

                #try:
                res = self.validator.validate( context, val )
                #except Invalid as e:
                #    e.value = val
                #    raise e

                if self.returnList is True:
                    result.append( res )
                else:
                    result[key] = res

        return result

    def _createContextChilds_on_value( self, context, value ):
        data = SchemaData( self.validateItem )
        data.isList = isinstance( value, list) or isinstance(value, tuple) or isinstance(value, set)

        if not data.isList:
            if not isinstance(value, dict ):
                raise Invalid( value, self,'type' )

        if self.returnList:
            result = []
        else:
            result = {}
        errors = []

        data.values = value
        context.setSchemaData( data )

        if data.isList or self.numericKeys:
            data.indexFunc = lambda index, schemaData: str(index)

            for pos in range( len( value ) ):
                if not data.isList:
                    if value.get(str(pos),MISSING) is MISSING:
                        context.resetSchemaData()
                        raise Invalid( value, self, 'numericKeys',keys=value.keys())

                try:
                    res = context( pos ).result
                except Invalid as e:
                    errors.append( context.key )
                else:
                    if self.returnList:
                        result.append( res )
                    else:
                        result[ contextKey ] =  res
        else:
            if self.returnList:
                raise Invalid( value, self, 'listType' )
            for key in value.keys():
                try:
                    result[ key ] = context( key ).result
                except Invalid as e:
                    errors.append( key )

        context.resetSchemaData()

        if errors:
            raise Invalid( value, self, errors=errors )

        return result


class FieldValidator( Validator ):

    def setParameters(self):
        raise SyntaxError( "FieldValidator cannot be used directly" )

    def getField( self, context, path):
        pathSplit = path.split('.')

        if pathSplit[0].startswith('/'):
            pathSplit[0] = pathSplit[0][1:]
            fieldcontext = context.root
        else:
            fieldcontext = context

            while fieldcontext.parent and pathSplit and pathSplit[0] is '':
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

    def setParameters(self, path, criteria=None, useResult=False, copy=False, writeToContext=False):
        self.path = path
        self.copy = copy
        self.useResult = useResult
        self.writeToContext = writeToContext

        if criteria is None:
            self.copy = True
        elif not isinstance( criteria, ValidatorBase):
            criteria = Match( criteria )

        self.validator  = criteria

    def appendSubValidators( self, subValidators ):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def validate(self, context, value):
        fieldcontext = self.getField( context, self.path )

        result = PASS

        if not self.useResult:
            result = fieldcontext.value

        else:
            try:
                result = fieldcontext.result
            except Invalid as e:
                result = PASS

        if self.validator is not None:
            if result is not PASS:
                result = self.validator.validate( fieldcontext, result )

        if self.writeToContext is True:
            fieldcontext.__result__ = result

        if self.copy:
            if result is PASS:
                return value

            return result

        return value
