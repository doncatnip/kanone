from ..lib import messages, MISSING, PASS, ValidatorBase
from ..error import Invalid

import logging, copy

log = logging.getLogger(__name__)


class Validator ( ValidatorBase ):

    messages\
        ( missing= 'Please provide a value'
        , blank='Field cannot be empty'
        )

    def __validate__( self, validatorfunc ):
        def wrapValidate( nself, context, value ):
            try:
                return validatorfunc( nself, context, value )
            except Invalid,e:
                if e.validator is None:
                    e.validator = nself

                    if 'catchall' in nself.__messages__:
                        msg = nself.__messages__['catchall']
                    else:
                        msg = nself.__messages__[e.key]

                    e.msg = msg
                    e.context = context
                raise e

        return wrapValidate

    def __new__( klass, *args, enabled=True, **kwargs ):
        self = ValidatorBase.__new__( klass )

        pre_validators = list(getattr( klass, '__pre_validate__', [] ))
        post_validators = list(getattr( klass, '__post_validate__', [] ))

        if hasattr( self, '__prepare__' ):
            pre_validators,post_validators = self.__prepare__(  pre_validators, post_validators, *args, **kwargs )
        else:
            self.__init__( *args, **kwargs )

        validator = self

        if pre_validators or post_validators:

            if not isinstance( self, And ):
                validator = And ( *(pre_validators + [ self ] + post_validators) )
            else:
                self.__validators__ = pre_validators + self.__validators__ + post_validators;
                validator = self

        validator.validate = validator.__validate__( validator.validate )
        validator.__args__ = args
        validator.__kwargs__ = kwargs

        return validator

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

    def __call__( self,*args,**kwargs ):

        if not args:
            valargs = self.__args__
        else:
            valargs = args

        valkwargs = dict(self.__kwargs__)
        valkwargs.update( kwargs )

        validator = self.__class__( *valargs, **valkwargs)
        validator.__messages__ = dict(self.__messages__)

        return validator

    def on_value( self, context, value ):
        return value

    def on_missing(self, context):
        raise Invalid( 'missing' )

    def on_blank(self, context):
        raise Invalid( 'blank' )


class Pass( Validator ):

    def validate( self, context, value ):
        return PASS



class Not( Validator ):

    messages\
        ( fail='Field must not match criteria'
        )

    def __init__(self, criteria):
        #if not isinstance( criteria, Validator ):
        #    criteria = Match( criteria )
        self.validator = criteria

    def appendSubValidators( self, subValidators):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def validate(self, context, value ):
        try:
            result = self.validator.validate( context, value )
        except Invalid:
            return value

        raise Invalid('fail')


class And( Validator ):

    def __init__(self, chain_result=True, *criteria ):
        self.chain_result = chain_result

        criteria = list(criteria)
        #for pos in range(len(criteria)):
        #    if not isinstance(criteria[pos], Validator):
        #        criteria[pos] = Match(criteria[pos])

        self.__validators__ = criteria

    def appendSubValidators( self, subValidators):
        for validator in self.__validators__:
            validator.appendSubValidators( subValidators )
            subValidators.append( validator )

    def validate(self, context, value):
        result = value

        for validator in self.__validators__:
            try:
                result = validator.validate( context, value )
                if self.chain_result:
                    value = result

            except Invalid,e:
                if ('catchall' in self.__messages__):
                    e = Invalid('catchall')
                raise e

        return result


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

class Tag( Validator ):

    def __init__( self, tag, validator, enabled=True ):
        self.validator = validator
        self.tag = tag
        self.enabled = enabled

    def appendSubValidators( self, subValidators ):
        self.validator.appendSubValidators( subValidators )
        subValidators.append( self.validator )

    def validate( self, context, value ):
        return self.validator.validate( context, value )

    def tag( self, tag ):
        raise SyntaxError( "This validator (%s) is allready tagged" % self.validator )


def __parseTaggedKeywords( **kwargs ):

    tagKwargs = {}
    validatorKwargs = {}

    for (key,value) in kwargs:
        tagPath = key.split('_',1)
    
        if len(tagPath)==2:
            if tagPath[0] not in tagKwargs:
                tagKwargs[tagPath[0]] = {}
            tagKwargs[tagPath[0]][tagPath[1]] = value
        else:
            validatorKwargs[tagPath[0]] = value

    return (tagKwargs, validatorKwargs )


class TagContainer( Validator ):

    def __init__( self, validator, tags )
        self.validator  = validator
        self.tags       = tags

    def validate(self, context, value):
        return self.validator.validate( context, valie )

    def messages(self, **kwargs):
        (tagKwargs,validatorKwargs) = __parseTaggedKeywords( **kwargs )

        for (tag, kwargs) in tagKwargs:
            if not tag in self.tags:
                raise SyntaxError("No tagged validator named %s found" % tag)

            self.tags[tag].messages( **kwargs )

        self.validator.messages( ** validatorKwargs )


class Tagger( Validator ):

    def __init__( self, validator ):
        self.validator = validator

    def __call__( self, **kwargs ):

        validator = copy.deepcopy(self.validator)

        validators = [ validator ]
        validator.appendSubValidators( validators )

        taggedValidators = {}
        for validator in validators:
            if isinstance( validator, Tag ):
                taggedValidators[validator.tag] = validator


        (tagKwargs,validatorKwargs) = __parseTaggedKeywords( **kwargs )

        for (tag, taggedKwargs) in tagKwargs:
            if not tag in taggedValidators:
                raise SyntaxError("No tagged validator named %s found" % tag)

            taggedValidator = taggedValidators[ tag ]
            for (key,arg) in taggedKwargs:
                if hasattr(taggedValidators, key):
                    setattr(taggedValidator, key, arg)

        for (key, arg) in validatorKwargs:
            if hasattr(validator,key):
                setattr( validator, key, arg )

        validator = TagContainer(validator, taggedValidators )
        validator.messages( **self.__messages__ )

    def validate( self, context, value ):
        raise SyntaxError("A tagger cannot validate directly, please use MyTagger() first")

    def tag(self, tag):
        raise SyntaxError("A tagger cannot be tagged directly, please use MyTagger() first")
