from ..lib import messages, MISSING, Parameterized, inherit
from ..error import Invalid

import logging, copy

log = logging.getLogger(__name__)


#### Basic stuff

# validators without messages and changeable parameters should derive from this
class ValidatorBase(object):

    def __new__( klass, *args, **kwargs ):
        self = object.__new__( klass )

        preValidators =\
            getattr(klass,'__pre_validate__',[])
        postValidators =\
            getattr(klass,'__post_validate__',[])

        if preValidators or preValidators:
            self.__init__( *args, **kwargs )
            self = And( *preValidators + [ self ] + postValidators )

        return self

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

    def __init__( self, *args, **kwargs ):
        Parameterized.__init__( self, *args, **kwargs )

        #self.__class__.validate = getattr(self.__class__,'validate',self.__class__.on_value)

    def invalid( self, _context, _error='fail', value=MISSING, **extra ):
        if value is MISSING:
            value = _context.value;

        if not isinstance(_error,Invalid):
             e = Invalid(_error, **extra)

        msg = self.__messages__.get('catchall',None)
        msg = msg or self.__messages__[e.key]

        e.validator = self
        e.context = _context
        e.extra['value'] = value

        if msg is not None:
            e.data['message'] = msg

        return e

    def validate( self, context, value ):
        if value is MISSING:
            return self.on_missing( context )
        elif value is None or value is '' or value is b'':
            self.on_blank( context )

        return self.on_value( context, value )


    def messages( self, **messages):
        self.__messages__ = dict( self.__messages__ )
        self.__messages__.update( messages )
        return self

    def on_value( self, context, value ):
        return value

    def on_missing(self, context):
        raise self.invalid( context, 'missing' )

    def on_blank(self, context):
        raise self.invalid( context, 'blank' )


class Tag( ValidatorBase ):

    _id = 0

    def __init__( self, validator, tagName, enabled=True):
        if isinstance( validator, Tag ):
            raise SyntaxError('%s is not taggable' % validator.__class__.__name__ )

        self.validator = validator
        self.tagName = tagName
        self.enabled = enabled
        self.tagID = Tag._id
        Tag._id += 1

    def appendSubValidators( self, subValidators ):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def validate( self, context, value ):
        validator = context.root.taggedValidators.get(self.tagID, None)
        if validator is None:
            validator = self.enabled and self.validator

        return validator\
            and validator.validate( context, value )\
            or value



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

    for (key,value) in kwargs.iteritems():
        if key.startswith('_'):
            continue

        if alias and (key in alias):
            if isinstance( alias[key], tuple ):
                for realKey in alias[key]:
                    _setParsedKeywordArg( tagKwargs, realKey, value )
            elif hasattr( alias[key], '__call__' ):
                realKwargs = alias[key]( key, value )
                for (realKey, realValue) in realKwargs.iteritems():
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
        , 'tagIDs'
        , 'taggedValidators'
        , 'currentTaggedValidators'
        , 'validator'
        )

    paramAlias = None
    messageAlias = None

    taggedValidators = {}

    def setArguments( self, validator ):
        self.validator = validator
        self.taggedValidators = {}
        self.currentTaggedValidators = {}
        self.tagIDs = {}

        subValidators = [ self.validator ]
        self.validator.appendSubValidators( subValidators )

        for validator in subValidators:
            if isinstance( validator, Tag ):
                if not validator.tagName in self.tagIDs:
                    self.tagIDs[validator.tagName] = []
                self.taggedValidators[ validator.tagID ] = validator.validator
                self.currentTaggedValidators[ validator.tagID ] = validator.enabled and validator.validator
                self.tagIDs[validator.tagName].append(validator.tagID)
        if not self.tagIDs:
            raise SyntaxError('No tags found.')

    def setParameters( self, **kwargs):
        taggedKwargs = _parseTaggedKeywords( kwargs, self.paramAlias )

        notFound = []
        self.__clonedTaggedValidators = []

        if not self.__isRoot__:
            self.currentTaggedValidators = dict( self.currentTaggedValidators )

        for (tagName, args) in taggedKwargs.iteritems():
            tagIDs = self.tagIDs.get( tagName, None )
            if tagIDs is None:
                notFound.append( tagName )
            else:
                enabled = args.pop('enabled',True)
                for tagID in tagIDs:
                    if not enabled:
                        self.currentTaggedValidators[ tagID ] = False
                    else:
                        if args:
                            validator =\
                                self.taggedValidators[ tagID ] =\
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
        finally:
            context.root.taggedValidators = tmpTags

    def messages( self, **kwargs ):
        taggedKwargs = _parseTaggedKeywords( kwargs, self.messageAlias )

        notFound = []

        for (tagName,args) in taggedKwargs.iteritems():
            tagIDs = self.tagIDs.get(tagName,None)
            if tagIDs is None:
                notFound.append( tagName )
            else:
                for tagID in tagIDs:
                    if tagID not in self.__clonedTaggedValidators:
                        taggedValidator = self.currentTaggedValidators[tagID]\
                            = self.taggedValidators[tagID]\
                            = self.taggedValidators[tagID]()
                        self.__clonedTaggedValidators.append ( tagID )
                    else:
                        taggedValidator = taggedValidators[tagID]

                    taggedValidator.messages( **args )

        if notFound:
            raise SyntaxError('messages: Tags %s not found' % str(notFound))

        return self

    def messageAlias( self, **alias ):
        self.messageAlias = alias
        return self

    def paramAlias( self, **alias ):
        self.paramAlias = alias
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
            if self.raiseError is True:
                raise

        return value


class Item( Validator ):

    messages\
        ( type='Unsupported type, must be list-like or dict'
        , notFound='Item %(key)s not found'
        )

    def setParameters( self, key=1, validator=None, alter=None ):
        if not validator and alter:
            raise SyntaxError('alter can only be set to True, if a validator is given')

        self.key = key
        self.validator = validator
        self.alter = alter is None and validator is not None or alter

    def appendSubValidators( self, subValidators ):
        subValidators.append( self.validator )
        self.validator.appendSubValidators( subValidators )

    def validate( self, context, value ):
        try:
            val = value[ self.key ]
        except TypeError:
            raise self.invalid(context, 'type', value )
        except (KeyError, IndexError):
            raise self.invalid(context, 'notFound', value, key=self.key )
        else:
            if self.validator is not None:
                val = self.validator.validate( context, val )

                if self.alter:
                    value[self.key] = val
                return value
            else:
                return val



class Pass( ValidatorBase ):

    def __init__( self ):
        self.validate = lambda context, value: value


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

        raise self.invalid(context, value=value)


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
            except Invalid as e:
                errors.append( e.data )
                continue

            return result
        if errors:
            raise self.invalid(context, value=value, errors=errors)

        return value

    def __or__( self, other ):
        self.validators.append( other )
        return self


class Call( Validator ):

    def setParameters( self, func ):
        self.__func__ = func

    def validate( self, context, value ):
        return self.__func__( context, value )



