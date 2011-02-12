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

        if not pre_validators and not post_validators:
            return self

        if not isinstance( self, And ):
            validator = And ( *(pre_validators + [ self ] + post_validators) )
        else:
            self.__validators__ = pre_validators + self.__validators__ + post_validators;
            validator = self

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

    def on_value( self, context, value ):
        return value

    def on_missing(self, context):
        raise self.invalid( 'missing' )

    def on_blank(self, context):
        raise self.invalid( 'blank' )



class Pass( Validator ):

    def on_missing self, context ):
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
            self.__update__ = required.__update__

        self.__ignore_case__ = ignore_case
        self.required = required

    def populate(self, context, value):
        return self.required.populate( context, value )

    def validate(self, context, value ):

        if self.type is Match.REGEX:
            if not self.pattern.match(value):
                raise self.invalid('missmatch', type=self.type, criteria=required.pattern)
            return value
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
            raise self.invalid( 'misssmatch', type=self.type, critaria=compare )

        return PASS

class Not( Validator ):

    messages\
        ( match='Field must not match criteria'
        )

    def __init__(self, criteria):
        if not isinstance( criteria, Validator ):
            criteria = Match( criteria )
        self.validator = criteria
        self.__update__ = criteria.__update__

    def populate(self, context, value):
        return self.validator.populate( context, value)

    def validate(self, context, value ):
        try:
            result = self.validator.validate( context )
        except Invalid:
            return value

        raise self.invalid('match')


class And( Validator ):

    __update__ = True

    def __init__(self, *criteria ):

        criteria = list(criteria)
        for pos in range(len(criteria)):
            if not isinstance(criteria[pos], Validator):
                criteria[pos] = Match(criteria[pos])

        self.__validators__ = criteria

    def populate(self, context, value):
        result = value

        for validator in self.__validators__:
            if validator.__update__:
                result = value = validator.populate( context, value )
            try:
                result = validator.validate( context, result )
            except Invalid,e:
                if ('catchall' in self.__messages__)
                    e = self.invalid('catchall')
                context.data( self ).error = e
                return value

        context.data( self ).result = result

        return value

    def validate(self, context, value):
        if context.data( self ).error:
            raise context.data( self ).error
        return context.data( self ).result


class Or( And ):

    messages\
        ( fail='No criteria met (Errors: %(errors)s)'
        )

    def populate(self, context, value):
        errors = []

        for validator in self.__validators__:
            if validator.__update__:
                result = value = validator.populate( context, value  )
            try:
                result = validator.validate( context, result )
            except Invalid, e:
                errors.append( e )
                continue

            context.data( self ).result = result
            return value

        if errors:
            context.data( self ).error = self.invalid(errors=errors)
        else:
            context.data( self ).result = value

        return value


class Call( Validator ):

    def __init__( self, validate=None, populate=None ):
        if validate is None and populate is None:
            raise SyntaxError("Call validator needs atleast one of these arguments: Call(validate=valFunc,populate=popFunc)")
        self.__func_validate__ = validate
        selt.__update__ = populate is not None 
        self.__func_populate__ = populate

    def validate( self, context, value ):
        if self.__func_validate__ is None:
            return value
        return self.__func_validate__( context, value )

    def populate( self, context, value ):
        return self.__func_populate__( context, value )
