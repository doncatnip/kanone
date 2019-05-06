from ..lib import Context as __Context__, MISSING, PASS, inherit, Parameterized
from ..error import Invalid

import logging
from functools import reduce

log = logging.getLogger(__name__)

#### Basic stuff

def messages( **_messages ):
    def decorate( klass ):
        klassMessages = dict(getattr(klass,'__messages__', {} ))
        klassMessages.update( _messages )

        setattr( klass, '__messages__', klassMessages )
        return klass

    return decorate


def validator2parameter( hostValidator, name, param, force=False ):
    paramWrapper =  getattr(hostValidator,'__paramWrapper__',None)
    if not paramWrapper:
        class ParamWrapper:
            def __init__( self, context, value ):
                self.__context = context
                self.__value = value

        hostValidator.__paramWrapper__ =\
            paramWrapper =\
            ParamWrapper

        validate = hostValidator.validate
        def wrapped( context, value ):
            context.params = paramWrapper( context, value )
            return validate( context, value )

        hostValidator.validate = wrapped

    if isinstance(param, ValidatorBase ):
        hostValidator.__paramValidators__.append( param )
        prop = property(lambda self: param.validate( self.__context, self.__value ))
    else:
        if force:
            raise SyntaxError('Parameter has to be a validator')
        prop = param
        
    setattr( paramWrapper, name, prop )


# validators without messages and changeable parameters should derive from this
class ValidatorBase(object):

    def __new__( cls, *args, **kwargs ):
        self = object.__new__( cls )

        preValidators =\
            getattr(cls,'__pre_validate__',[])
        postValidators =\
            getattr(cls,'__post_validate__',[])

        if preValidators or preValidators:
            self.__init__( *args, **kwargs )
            self = And( *preValidators + [ self ] + postValidators )

        return self

    def appendSubValidators( self, subValidators ):
        pass

    def __and__( self, other ):
        if isinstance(other, And):
            return And(*[self]+other.validators)
        return And( self, other )

    def __or__( self, other ):
        if isinstance(other, Or):
            return Or(*[self]+other.validators)
        return Or( self, other )

    def __invert__( self ):
        return Not( self )

    def tag( self, tagName, enabled=True ):
        return Tag( self, tagName, enabled )

    def context( self, value=MISSING ):
        return __Context__( self, value )

    # just a passthrough for convinience
    def __call__( self ):
        return self

@messages\
    ( fail='Validation failed'
    , missing= 'Please provide a value'
    , blank='Field cannot be empty'
    )
@inherit\
    ( '__messages__'
    )
class Validator( Parameterized, ValidatorBase ):

    def __init__( self, *args, **kwargs ):
        Parameterized.__init__( self, *args, **kwargs )

    def validate( self, context, value ):
        if value is MISSING:
            return self.on_missing( context )
        elif value is None or (value == ''):
            return self.on_blank( context, value )

        return self.on_value( context, value )

    def messages( self, **messages):
        self.__messages__ = dict( self.__messages__ )
        self.__messages__.update( messages )
        return self

    def on_value( self, context, value ):
        return value

    def on_missing(self, context):
        raise Invalid( '', self, 'missing' )

    def on_blank(self, context, value ):
        raise Invalid( value, self, 'blank' )


class Tag( ValidatorBase ):

    _ID = 0

    def __init__( self, validator, tagName, enabled=True):
        if isinstance( validator, Tag ):
            raise SyntaxError('%s is not taggable' % validator.__class__.__name__ )

        self.validator = validator
        self.tagName = tagName
        self.enabled = enabled
        self.tagID = Tag._ID
        Tag._ID += 1

    def appendSubValidators( self, subValidators ):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def validate( self, context, value ):
        validator = context.root.taggedValidators.get(self.tagID, None)
        if validator is None:
            validator = self.enabled and self.validator

        if not validator:
            return value

        try:
            return validator.validate( context, value )
        except Invalid as e:
            if e.validator is validator or getattr(e,'composer',None) is validator:
                e.tagName = self.tagName
            raise e

def _setParsedKeywordArg( tagKwargs, key, value ):
    tagPath = key.split('_',1)

    theKwargs = tagKwargs.get(tagPath[0], None)
    if theKwargs is None:
        theKwargs = tagKwargs[tagPath[0]] = {}
   
    if len(tagPath)==2:
        theKwargs[tagPath[1]] = value
    else:
        # maybe TODO: we could use these values as varargs
        # but for now, just set it to raise an error if the tag
        # doesnt exist
        theKwargs['_none__'] = None

def _parseTaggedKeywords( kwargs, alias ):

    tagKwargs = {}

    for (key,value) in kwargs.items():
        if key.startswith('_'):
            continue

        if alias and (key in alias):
            if isinstance( alias[key], tuple ):
                for realKey in alias[key]:
                    _setParsedKeywordArg( tagKwargs, realKey, value )
            elif hasattr( alias[key], '__call__' ):
                realKwargs = alias[key]( key, value )
                for (realKey, realValue) in realKwargs.items():
                    _setParsedKeywordArg( tagKwargs, realKey, realValue )
            else:
                _setParsedKeywordArg( tagKwargs, alias[key], value )
            continue

        _setParsedKeywordArg( tagKwargs, key, value )

    return tagKwargs

@inherit\
    ( '__paramAlias__'
    , '__messageAlias__'
    , 'tagIDs'
    , 'taggedValidators'
    , 'currentTaggedValidators'
    , 'validator'
    )
class Compose( Validator ):

    """
    usage:
    UserName = Compose\
          ( String.convert().tag('string') & Len(min=5).tag('len')
          ).paramAlias( len='len_min' ).messageAlias(type='string_type')

    someUserName = UserName( len=8 ).message( type='Must be a string !' )

    An alias can be: single tag, list of tags, function receiving alias, value
    and returning dict { realtag:value, .. }
    """

    # stuff defined here will be inherited by children of this Validator


    __paramAlias__ = None
    __messageAlias__ = None

    taggedValidators = {}

    def setArguments( self, validator ):
        self.validator = validator
        self.taggedValidators = {}
        self.currentTaggedValidators = {}
        self.tagIDs = {}
        subValidators = [ self.validator ]
        self.validator.appendSubValidators( subValidators )

        for validator in subValidators:
            if isinstance( validator, Tag):
                tagName = validator.tagName
                tagID = validator.tagID
                enabled = validator.enabled
                validator = validator.validator
                if not tagName in self.tagIDs:
                    self.tagIDs[tagName] = []
                self.taggedValidators[ tagID ] = validator
                self.currentTaggedValidators[ tagID ] = enabled and validator
                self.tagIDs[tagName].append(tagID)

        if not self.tagIDs:
            raise SyntaxError('No tags found.')

    def setParameters( self, **kwargs):
        taggedKwargs = _parseTaggedKeywords( kwargs, self.__paramAlias__ )

        notFound = []
        self.__clonedTaggedValidators = []

        if not self.__isRoot__:
            self.taggedValidators = dict( self.taggedValidators )
            self.currentTaggedValidators = dict( self.currentTaggedValidators )

        for (tagName, args) in taggedKwargs.items():
            tagIDs = self.tagIDs.get( tagName, None )

            if tagIDs is None:
                notFound.append( tagName )
            else:
                enabled = args.pop('enabled',None)

                for tagID in tagIDs:
                    if enabled is not None:
                        self.currentTaggedValidators[ tagID ] =\
                            enabled and self.taggedValidators[ tagID ] or False
                    else:
                        if args:
                            self.taggedValidators[ tagID ] =\
                                validator =\
                                self.taggedValidators[ tagID ](**args)
                            self.__clonedTaggedValidators.append( tagID )
                        else:
                            validator = self.taggedValidators[ tagID ]

                        self.currentTaggedValidators[ tagID ]\
                            = validator

        if notFound:
            raise SyntaxError('setParameters: Tags %s not found' % str(notFound))

    def validate( self, context, value ):
        tmpTags = context.root.taggedValidators
        context.root.taggedValidators = self.currentTaggedValidators
        try:
            return self.validator.validate( context, value )
        except Invalid as e:
            if hasattr(e,'tagName'):
                e.realkey = "%s_%s" % (e.tagName, getattr(e,'realkey',e.key))
                e.composer = self
                del e.tagName
            raise e
        finally:
            context.root.taggedValidators = tmpTags

    def messages( self, **kwargs ):
        taggedKwargs = _parseTaggedKeywords( kwargs, self.__messageAlias__ )

        notFound = []

        for (tagName,args) in taggedKwargs.items():
            tagIDs = self.tagIDs.get(tagName,None)
            if tagIDs is None:
                notFound.append( tagName )
            else:
                for tagID in tagIDs:
                    if tagID not in self.__clonedTaggedValidators:
                        self.taggedValidators[tagID]\
                            = taggedValidator \
                            = self.taggedValidators[tagID]()
                        if self.currentTaggedValidators[tagID] is not False:
                            self.currentTaggedValidators[tagID] = taggedValidator

                        self.__clonedTaggedValidators.append ( tagID )
                    else:
                        taggedValidator = self.taggedValidators[tagID]

                    taggedValidator.messages( **args )

        if notFound:
            raise SyntaxError('messages: Tags %s not found' % str(notFound))

        return self

    def messageAlias( self, **alias ):
        self.__messageAlias__ = alias
        return self

    def paramAlias( self, **alias ):
        self.__paramAlias__ = alias
        return self


class Tmp( ValidatorBase ):

    def __init__( self, validator, raiseError=True ):
        self.validator = validator
        self.raiseError = raiseError

    def appendSubValidators( self, subValidators ):
        subValidators.append( self.validator )
        self.validator.appendSubValidators( subValidators )
        return subValidators

    def validate( self, context, value ):
        try:
            self.validator.validate( context, value )
        except Invalid:
            if self.raiseError:
                raise

        return value

@messages\
    ( type='Unsupported type, must be list-like or dict'
    , notFound='Item %(key)s not found'
    )
class Item( Validator ):

    def setParameters( self, key=1, validator=None, alter=None ):
        if not validator and alter:
            raise SyntaxError('alter can only be set to True, if a validator is given')

        self.key = key
        self.validator = validator
        if alter is not None:
            self.alter = alter
        else:
            self.alter = validator is not None

    def appendSubValidators( self, subValidators ):
        subValidators.append( self.validator )
        self.validator.appendSubValidators( subValidators )

    def validate( self, context, value ):
        try:
            val = value[ self.key ]
        except TypeError:
            raise Invalid( value, self, 'type' )
        except (KeyError, IndexError):
            raise Invalid( value, self, 'notFound', key=self.key )
        else:
            if self.validator is not None:
                val = self.validator.validate( context, val )

                if self.alter:
                    value[self.key] = val
                return value
            else:
                return val


class If( ValidatorBase ):

    def __init__( self, criterion, _then, _else=None):
        self.criterion = criterion
        self._then = _then
        self._else = _else

    def appendSubValidators( self, subValidators ):
        self.criterion.appendSubValidators( subValidators )
        self._then.appendSubValidators( subValidators )
        subValidators.append( self.criterion )
        subValidators.append( self._then )

        if self._else:
            self._else.appendSubValidators( subValidators )
            subValidators.append( self._else )

    def validate( self, context, value ):
        try:
            value = self.criterion.validate( context, value )
        except Invalid:
            if not self._else:
                raise
            value = self._else.validate( context, value)
        else:
            value = self._then.validate( context, value )

        return value

class Pass( Validator ):

    def setParameters( self, default=PASS):
        self.default = PASS

    def validate( self, context, value ):
        if self.default is PASS:
            return value

        return self.default

@messages\
    ( fail='Field must not match criterion'
    )
@inherit\
    ( 'validator'
    )
class Not( Validator ):

    def setArguments(self, criterion):
        self.validator = criterion

    def appendSubValidators( self, subValidators):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def validate(self, context, value ):
        try:
            self.validator.validate\
                ( context, value )
        except Invalid:
            return value

        raise Invalid( value, self )


class And( ValidatorBase ):

    def __init__( self, *validators ):
        assert len(validators)>=2
        self.validators = list(validators)

    def validate( self, context, value ):
        return reduce( lambda val, validator: validator.validate(context, val), self.validators, value)

    def appendSubValidators( self, subValidators):
        for validator in self.validators:
            validator.appendSubValidators( subValidators )
            subValidators.append( validator )

    def __and__( self, other ):
        return And(*self.validators+[other])

class Or( ValidatorBase ):

    def __init__( self, *validators ):
        assert len(validators)>=2
        self.validators = list(validators)

    def appendSubValidators( self, subValidators):
        for validator in self.validators:
            validator.appendSubValidators( subValidators )
            subValidators.append( validator )

    def validate(self, context, value):
        lastError = None

        for validator in self.validators:
            try:
                return validator.validate( context, value )
            except Invalid as e:
                lastError = e

        if lastError is not None:
            raise lastError

        return value

    def __or__( self, other ):
        return Or(*self.validators+[other])

class Call( Validator ):

    def setParameters( self, func ):
        self.__func__ = func

    def validate( self, context, value ):
        try:
            return self.__func__( context, value )
        except Invalid as e:
            e.validator = self
            raise e

