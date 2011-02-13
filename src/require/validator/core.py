from ..lib import messages, MISSING, PASS, ValidatorBase
from ..error import Invalid

import re, copy

import logging
log = logging.getLogger(__name__)


class Validator ( ValidatorBase ):

    messages\
        ( missing= 'Please provide a value'
        , blank='Field cannot be empty'
        )

    def __new__( klass, *args, **kwargs ):
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

    def clone( self,*args,**kwargs ):
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
        raise self.invalid( 'missing' )

    def on_blank(self, context):
        raise self.invalid( 'blank' )



class Pass( Validator ):

    def on_missing( self, context ):
        return PASS

    def on_blank ( self, context ):
        return PASS


class Missing( Validator ):

    messages\
        ( value='This field must be left out'
        )

    def __init__( self, default = PASS ):
        self.default = default

    def on_value( self, context, value ):
        raise self.invalid( 'value' )

    def on_missing( self, context ):
        return self.default

class Blank( Validator ):

    messages\
        ( value='This field must be blank'
        )

    def __init__( self, default = PASS ):
        self.default = default
        self.check_container = \
            isinstance( default, dict )\
            or  isinstance( default, list )\
            or  isinstance( default, tuple )

    def on_value( self, context, value ):
 
        if self.check_container \
        and not isinstance( value, str)\
        and ( isinstance( value, dict ) or isinstance( value, list ) or isinstance( value, tuple) ):
            n = MISSING
            if len(value) > 0:
                if isinstance( value, dict):
                    for (key, val) in value.iteritems():
                        if val not in [ MISSING, None, '']:
                            n = value
                            break

                elif isinstance( value, list) or isinstance( value, tuple ):
                    for val in value:
                        if val not in [ MISSING, None, '']:
                            n = value
                            break
            if n is MISSING:
                return self.default

        raise self.invalid( 'value' )

    def on_blank( self, context ):
        return self.default


class Empty( Blank, Missing ):

    messages\
        ( value='This field must be empty (missing or blank)'
        )



class Match( Validator ):

    messages\
        ( missmatch='Field must match criteria %(criteria)s'
        )

    RAW         = 'Match_RAW'
    REGEX       = 'Match_REGEX'
    VALIDATOR   = 'Match_VALIDATOR'

    __ignore_case__ = False

    def __init__(self, required, ignore_case=False):
        if not isinstance( required, ValidatorBase ):
            if callable(getattr( required, 'match', None )):
                self.type = Match.REGEX
            else:
                self.type = Match.RAW
        else:
            self.type = Match.VALIDATOR

        self.__ignore_case__ = ignore_case
        self.required = required

    def validate(self, context, value ):

        if self.type is Match.REGEX:
            if not self.pattern.match(value):
                raise self.invalid('missmatch', type=self.type, criteria=required.pattern)
            return PASS
        elif self.type is Match.RAW:
            compare = self.required
        elif self.type is Match.VALIDATOR:
            try:
                compare = self.required.validate( context, value )
            except Invalid,e:
                return PASS

        if self.__ignore_case__:
            compare = str(compare).lower()
            value = str(value).lower()

        if value <> compare:
            raise self.invalid( 'missmatch', type=self.type, critaria=compare )

        return PASS


class Not( Validator ):

    messages\
        ( match='Field must not match criteria'
        )

    def __init__(self, criteria):
        if not isinstance( criteria, Validator ):
            criteria = Match( criteria )
        self.validator = criteria

    def validate(self, context, value ):
        try:
            result = self.validator.validate( context, value )
        except Invalid:
            return value

        raise self.invalid('match')


class And( Validator ):

    def __init__(self, *criteria ):

        criteria = list(criteria)
        for pos in range(len(criteria)):
            if not isinstance(criteria[pos], Validator):
                criteria[pos] = Match(criteria[pos])

        self.__validators__ = criteria

    def validate(self, context, value):
        result = value

        for validator in self.__validators__:
            try:
                result = validator.validate( context, result )
            except Invalid,e:
                if ('catchall' in self.__messages__):
                    e = self.invalid('catchall')
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
            raise self.invalid(errors=errors)

        return value


class Call( Validator ):

    def __init__( self, func ):
        self.__func__ = func

    def validate( self, context, value ):
        return self.__func__( context, value )
