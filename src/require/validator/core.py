from ..lib import messages, MISSING, PASS, ValidatorBase
from ..error import Invalid

import logging, copy

log = logging.getLogger(__name__)


#### Basic stuff

class Parameterize( dict ):

    def __init__( self, validator, parent=None, args=None, kwargs=None ):
        dict.__init__( self )

        if kwargs is None:
            kwargs = {}
        if args is None:
            args = ()

        self.args = args
        self.kwargs = kwargs
        self.validator = validator

        self.appendSubValidators = self.validator.appendSubValidators

        if hasattr( self.validator, 'messages' ):
            self.messages = self.validator.messages

        if (hasattr(self.validator,'setParameters')):
            self.params = Parameters()
            self.validator.setParameters( params, *args, **kwargs )
            self.params.update( validator.params )
        else:
            self.params = validator.params

        return self

    def __setattr__(self,key, value):
        if not hasattr(self,key):
            self[key] = value
        else:
            
    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError,e:
            raise AttributeError('Parameter %s not found' % key )

    def __call__( self, *args, **kwargs ):
        if not args and not kwargs:
            return self

        return self.__class__( self.validator, args, kwargs )

    def messages( self, **messages ):
        self.params.messages = dict(self.messages)
        self.params.messages.update( messages )
        return self

    def __and__( self, other ):
        if isinstance( self, And ):
            self.__validators__.append( other )
            return self
        elif isinstance( other, And):
            other.__validators__.append( self )
            return other

        return And( self, other )

    def __or__(self, other ):
        if isinstance( self, Or ):
            self.__validators__.append( other )
            return self
        elif isinstance( other, Or ):
            other.__validators__.append( self )
            return other
        return Or( self, other )

    def __invert__( self ):
        return Not( self )



class ValidatorBase( object ):

    def __preinit__( klass, *args, **kwargs):
        pass

    def __new__( klass, *args, **kwargs ):
        self = klass.__preinit__( *args, **kwargs)

        pre_validators = getattr( klass, '__pre_validate__', [] )
        post_validators = getattr( klass, '__post_validate__', [] )

        if pre_validators or post_validators:
            if not isinstance( self, And ):
                self = And ( *(pre_validators + [ self ] + post_validators) )
            else:
                self.__validators__ = pre_validators + self.__validators__ + post_validators;

        return self


class Validator( ValidatorBase ):

    messages\
        ( fail='Validation failed'
        , missing= 'Please provide a value'
        , blank='Field cannot be empty'
        )

    tagName = None

    @classmethod
    def __preinit__( klass, *args, **kwargs):
        self = object.__new__( klass )
        self.params = Parameters()
        self.params.messages = self.__messages__
        self.validate = self.__wrapValidate__( self.validate )
        return self

    def __wrapValidate__( self, validatorfunc ):
        def wrapped(context, value):
            self.beforeValidate( context, value )
            try:
                return validatorfunc( context, value )
            except Invalid,e:
                if e.validator is None:
                    e.validator = self
                if 'catchall' in context.params.messages:
                    msg = context.params.messages['catchall']
                else:
                    msg = context.params.messages[e.key]

                e.msg = msg
                e.context = context

                raise e

        return wrapped


    def tag( self, name ):
        if self.tagName is not None:
            raise SyntaxError( "This validator (%s) is allready tagged" % self )
        self.tagName = name

    def appendSubValidators( self, params ):
        pass


    def beforeValidate( self, context ):
        context.params = None

        if self.tagName is not None and hasattr( context.root, 'taggedParameters' ):
            if context.params.tagName in context.root.taggedParameters:
                params = context.root.taggedParameters[ self.tagName ]

        if context.params is None:
            context.params = self.params

    def validate( self, context, value ):
        if (value is MISSING):
            return self.on_missing( context )
        elif (value is in [None,'',[],{}]):
            return self.on_blank( context )
        else:
            return self.on_value( context, value )


    def on_value( self, context, value ):
        return value

    def on_missing(self, context):
        raise Invalid( 'missing' )

    def on_blank(self, context):
        raise Invalid( 'blank' )





class ValidatorFactory( Validator ):

    _singletons = {}

    @classmethod
    def __preinit__(klass, *args, **kwargs):
        if not klass in _singletons
            self = Validator.__preinit__( klass, *args, **kwargs )
            _singletons[ klass ] = self
            return self

        return _singletons[ klass ]( *args, **kwargs )

    def __call__( self, *args, **kwargs):
        return Parameterize( self, args, kwargs )
        



#### Tagging stuff


def __setParsedKeywordArg( tagKwargs, key, value ):
    tagPath = key.split('_',1)
    
    if len(tagPath)==2:
        if tagPath[0] not in tagKwargs:
            tagKwargs[tagPath[0]] = {}
        tagKwargs[tagPath[0]][tagPath[1]] = value


def __parseTaggedKeywords( kwargs, alias ):

    tagKwargs = {}

    for (key,value) in kwargs:
        if key.startswith('_'):
            continue

        if key in alias:
            if alias[key] isinstance( tuple ):
                for realKey in alias[key]:
                    __setParsedKeywordArg( tagKwargs, realKey, value )
            elif hasattr( alias[key], '__call__' ):
                realKwargs = alias[key]( key, value )
                for (realKey, realValue) in realKwargs:
                    __setParsedKeywordArg( tagKwargs, realKey, realValue )
            else:
                _setParsedKeywordArg( tagKwargs, alias[key], value )
            continue

        _setParsedKeywordArg( tagKwargs, key, value )

    return tagKwargs


class Tagger( ValidatorFactory ):

    def __init__( self, validator, paramAlias, messageAlias,  **kwargs ):
        self.validator = validator
        self.paramAlias = paramAlias
        self.messageAlias = messageAlias
        taggedValidators = [ validator ]
        validators = validator.appendSubValidators( taggedValidators )


    def setParameters( params, validator=None, paramAlias=None, messageAlias=None, **taggedParams )
        taggedParameters = __parseTaggedKeywords( taggedParams, params.paramAlias )
        params.taggedParameters = {}

        for (tag, theParams) in taggedParameters:
            if tag in self.taggedValidators:
                newParams = Parameters( self.taggedValidators[tag].validator.params )
                self.taggedValidators[tag].setParameters( params, **theParams )

                params.taggedParameters[tag] = newParams


    def validate(self, context, value):
        context.root.taggedParameters = context.params.taggedParameters
        try:
            return self.validator.validate( context, value )
        finally:
            if previousTagger is not None:
                context.root.taggedParameters = previousTagger


    def messages( self, **taggedMessages ):
        taggedMessages = __parseTaggedKeywords( taggedMessages, self.messageAlias )


# just a lil helper
# usage:
# UserName = Compose\
#       ( String.convert.tag('string') & Len(min=5).tag('len')
#       ).paramAlias( len='len_min' ).messageAlias(type='string_type')
#
# someUserName = UserName( len=8 ).message( type='Must be a string !' )
#
# An alias can be: single tag, list of tags, function receiving alias, value
# and returning dict { realtag:value, .. }
class Compose( object ):

    paramAlias = {}
    messageAlias = {}

    def __init__( self, validator ):
        self.validator = validator

    def __call__( self, **kwargs ):
        return Tagger( self.validator, self.paramAlias, self.messageAlias, **kwargs )

    def messageAlias( self, **alias ):
        self.messageAlias = alias
        return self

    def paramAlias( self, **alias ):
        self.paramAlias = alias
        return self


#### Validators


# is an 'Immutable'
class __Pass__( Validator ):

    def validate( self, context, value ):
        return PASS

Pass = __Pass__()


class Not( ValidatorFactory ):

    messages\
        ( fail='Field must not match criteria'
        )

    def setParameters_(self, params, criteria):
        params.validator = criteria

    def appendSubValidators( self, params, subValidators):
        params.validator.appendSubValidators( subValidators )
        subValidators.append( params.validator )

    def validate(self, context, value ):
        try:
            result = self.validator.validate( context, value )
        except Invalid:
            return value

        raise Invalid('fail')


class And( ValidatorFactory ):

    def setParameters( self, params, validators, chainResult=True ):
        params.chainResult = chainResult
        data.validators = list(validators)

    def appendSubValidators( self, data, subValidators):
        for validator in data.validators:
            validator.appendSubValidators( subValidators )
            subValidators.append( validator )

    def validate(self, context, value):
        result = value

        for validator in self.__validators__:
            try:
                result = validator.validate( context, value )
                if context.data.chain_result:
                    value = result

            except Invalid,e:
                if ('catchall' in self.__messages__):
                    e = Invalid('catchall')
                raise e

        return result

And = __And__()


class Or( And ):

    messages\
        ( fail='No criteria met (Errors: %(errors)s)'
        )

    def validate(self, context, value):
        errors = []
        result = value

        for validator in self.__validators__:
            try:
                result = validator.validate( context, result )
            except Invalid, e:
                errors.append( e )
                continue

            return result

        if errors:
            raise Invalid(errors=errors)

        return value


class Call( Validator ):

    def __init__( self, func ):
        self.__func__ = func

    def validate( self, context, value ):
        return self.__func__( context, value )



