from ..lib import messages, MISSING, Parameterized, inherit
from ..error import Invalid

import logging, copy

log = logging.getLogger(__name__)


#### Basic stuff

# validators without messages and changeable parameters should derive from this
class ValidatorBase(object):

    def appendSubValidators( self, subValidators ):
        pass

    def __and__( self, other ):
        if isinstance(other, And):
            other.validators.insert(0, self)
            return other
        return And( self, other )

    def __or__( self, other ):
        if isinstance(other, Or):
            other.validators.insert(0,self)
        return Or( self, other )

    def __invert__( self ):
        return Not( self )

    def tag( self, tagName, enabled=True ):
        return Tag( self, tagName, enabled )


class Validator( Parameterized, ValidatorBase ):

    messages\
        ( fail='Validation failed'
        , missing= 'Please provide a value'
        , blank='Field cannot be empty'
        )

    inherit\
        ( '__messages__'
        )

    __isValidateWrapped__ = False

    def __new__( klass, *args, **kwargs ):
        if not klass.__isValidateWrapped__:
            klass.validate = klass.__wrapValidate__( klass.validate )
            klass.__isValidateWrapped__ = True
        self = object.__new__( klass )
        return self

    @classmethod
    def __wrapValidate__( klass, validateFunc ):
        def wrappedValidate( self, context, value ):
            return klass.doValidate\
                and klass.doValidate( self, validateFunc, context, value )\
                or validateFunc( self, context, value )

        return wrappedValidate

    @classmethod
    def doValidate( klass, validator, validateFunc, context, value ):
        try:
            return validateFunc( validator, context, value )
        except Invalid, e:
            msg = validator.__messages__.get('catchall',None)

            if e.validator is None:
                msg = msg or validator.__messages__[e.key]
                e.validator = validator
                e.context = context
                e.extra['value'] = value
            if msg is not None:
                e.message = msg

            raise e


    def messages( self, **messages):
        self.__messages__ = dict( self.__messages__ )
        self.__messages__.update( messages )
        return self

    def validate( self, context, value ):
        if (value is MISSING):
            return self.on_missing( context )
        elif (value in [None,'',[],{}]):
            return self.on_blank( context )
        else:
            return self.on_value( context, value )

    def on_value( self, context, value ):
        return value

    def on_missing(self, context):
        raise Invalid( 'missing' )

    def on_blank(self, context):
        raise Invalid( 'blank' )


class Tag( ValidatorBase ):

    _id = 0

    def __init__( self, validator, tagName, enabled=True):
        if isinstance( validator, Tag ):
            raise SyntaxError('%s is not taggable' % validator.__class__.__name__ )

        self.validator = validator
        self.tagName = tagName
        self.enabled = enabled
        self.tagId = Tag._id
        Tag._id += 1

    def appendSubValidators( self, subValidators ):
        self.validator.appendSubValidators( subValidators )

    def validate( self, context, value ):
        tags = getattr(context.root, 'taggedValidators',None)
        validator = False

        if tags and self.tagId in tags:
            validator = tags[ self.tagId ]
        elif self.enabled:
            validator = self.validator
        if validator is not False:
            return validator.validate( context, value )
        return value


def _setParsedKeywordArg( tagKwargs, key, value ):
    tagPath = key.split('_',1)
    
    if len(tagPath)==2:
        if tagPath[0] not in tagKwargs:
            tagKwargs[tagPath[0]] = {}
        tagKwargs[tagPath[0]][tagPath[1]] = value


def _parseTaggedKeywords( kwargs, alias ):

    tagKwargs = {}

    for (key,value) in kwargs.iteritems():
        if key.startswith('_'):
            continue

        if alias and (key in alias):
            if isinstance( alias[key], tuple ):
                for realKey in alias[key]:
                    _setParsedKeywordArg( tagKwargs, realKey, value )
            elif hasattr( alias[key], '__call__' ):
                realKwargs = alias[key]( key, value )
                for (realKey, realValue) in realKwargs:
                    _setParsedKeywordArg( tagKwargs, realKey, realValue )
            else:
                _setParsedKeywordArg( tagKwargs, alias[key], value )
            continue

        _setParsedKeywordArg( tagKwargs, key, value )

    return tagKwargs


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

    # stuff defined here will be inherited by childs of this Validator
    inherit\
        ( 'paramAlias'
        , 'messageAlias'
        , 'tags'
        , 'validator'
        )

    paramAlias = None
    messageAlias = None

    taggedValidators = {}

    def setArguments( self, validator ):
        self.validator = validator
        self.tags = {}

        subValidators = [ self.validator ]
        self.validator.appendSubValidators( subValidators )

        for validator in subValidators:
            if isinstance( validator, Tag ):
                if not validator.tagName in self.tags:
                    self.tags[validator.tagName] = []
                self.tags[validator.tagName].append(validator)

        if not self.tags:
            raise SyntaxError('No tags found.')

    def setParameters( self, **kwargs):
        taggedKwargs = _parseTaggedKeywords( kwargs, self.paramAlias )

        self.taggedValidators = {}
        notFound = []

        if not self.__isRoot__:
            self.tags = dict( self.tags )

        for (tagName, args) in taggedKwargs.iteritems():
            if not tagName in self.tags:
                notFound.append( tagName )
            else:
                enabled = args.pop('enabled',True)

                for tag in self.tags[ tagName ]:
                    validator = enabled\
                        and ( args and tag.validator( **args )\
                              or tag.validator )\
                        or False

                    self.taggedValidators[ tag.tagId ] = validator

        if notFound:
            raise SyntaxError('Tags %s not found' % str(notFound))


    def appendSubValidators( self, subValidators ):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def validate( self, context, value ):
        context.root.taggedValidators = self.taggedValidators
        try:
            return self.validator.validate( context, value )
        finally:
            del context.root.taggedValidators

    def messages( self, **kwargs ):
        taggedKwargs = _parseTaggedKeywords( kwargs, self.messageAlias )

        for (tagName,args) in taggedKwargs.iteritems():
            if tagName in self.tags:
                for tag in self.tags[tagName]:
                    taggedValidator = tag.validator
                    if not tag.tagId in self.taggedValidators:
                        self.taggedValidators[tag.tagId] = taggedValidator()
                    taggedValidator.messages( **args )

        return self

    def messageAlias( self, **alias ):
        self.messageAlias = alias
        return self

    def paramAlias( self, **alias ):
        self.paramAlias = alias
        return self



class Pass( ValidatorBase ):

    def validate( self, context, value ):
        return value



class Not( Validator ):

    messages\
        ( fail='Field must not match criteria'
        )

    inherit\
        ( 'validator'
        )

    def setArguments(self, criteria):
        self.validator = criteria

    def appendSubValidators( self, subValidators):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def validate(self, context, value ):
        try:
            result = self.validator.validate\
                ( context, value )
        except Invalid:
            return value

        raise Invalid('fail')


class And( Validator ):

    inherit\
        ( 'validators'
        )

    def setArguments( self, *validators ):
        assert len(validators)>=2
        self.validators = list(validators)

    def setParameters( self, chainResult=True ):
        self.chainResult = chainResult

    def appendSubValidators( self, subValidators):
        for validator in self.validators:
            validator.appendSubValidators( subValidators )
            subValidators.append( validator )

    def validate(self, context, value):
        result = value

        for validator in self.validators:
            result = validator.validate( context, value )
            if self.chainResult:
                value = result

        return result

    def __and__( self, other ):
        self.validators.append( other )
        return self


class Or( Validator ):

    messages\
        ( fail='No criteria met (Errors: %(errors)s)'
        )

    inherit\
        ( 'validators'
        )

    def setArguments( self, *validators ):
        assert len(validators)>=2
        self.validators = list(validators)

    def appendSubValidators( self, subValidators):
        for validator in self.validators:
            validator.appendSubValidators( subValidators )
            subValidators.append( validator )

    def validate(self, context, value):
        errors = []
        result = value

        for validator in self.validators:
            try:
                result = validator.validate( context, result )
            except Invalid, e:
                errors.append( e )
                continue

            return result
        if errors:
            raise Invalid(errors=errors)

        return value

    def __or__( self, other ):
        self.validators.append( other )
        return self


class Call( Validator ):

    def setParameters( self, func ):
        self.__func__ = func

    def validate( self, context, value ):
        return self.__func__( context, value )



