from ..lib import pre_validate, missing, IGNORE, ValidationState, ValidatorBase, SchemaBase
from ..error import *
from .. import settings as s

import re, copy

import logging
log = logging.getLogger(__name__)

class SchemaFailed(Exception):
    pass

def schema_failed( context):
    raise SchemaFailed


class Validator ( ValidatorBase ):

    msg                 = s.text.Validator.msg

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

    def __new__( klass, *args, **kwargs ):
        self = ValidatorBase.__new__( klass )

        if isinstance( self, And ):
            return self

        pre_validators = list(getattr( klass, '__pre_validate__', [] ))

        prepare = getattr( self, '__prepare__', False)
        if prepare:
            pre_validators = self.__prepare__(  pre_validators, *args, **kwargs )

        if not pre_validators:
            return self

        if not prepare:
            self.__init__( *args, **kwargs )
        else:
            self.__init__( )

        validator = And ( *pre_validators  ) & self

        return validator

    def on_value( self, context, value):
        return value

    def on_missing(self, context):
        raise Invalid( Validator.msg[0] )

    def on_blank(self, context):
        raise Invalid( Validator.msg[1] )

class Pass( Validator ):

    def on_missing( self, context ):
        return IGNORE

    def on_blank ( self, context):
        return IGNORE


class Missing( Validator ):

    info = s.text.Missing.info
    msg  = s.text.Missing.msg

    def __init__( self, default = IGNORE ):
        self.default = default

    def on_value( self, context, value ):
        raise Invalid( self.msg )

    def on_missing( self, context ):
        return self.default

class Blank( Validator ):
    info = s.text.Blank.info
    msg  = s.text.Blank.msg

    def __init__( self, default = IGNORE ):
        self.default = default
        self.check_container = \
            isinstance( default, dict )\
            or  isinstance( default, list )\
            or  isinstance( default, tuple )

    def on_value( self, context, value):
 
        if isinstance( value, ValidationState ):
            value = value.__values__

        if self.check_container \
        and not isinstance( value, str)\
        and ( isinstance( value, dict ) or isinstance( value, list ) or isinstance( value, tuple) ):
            n = missing
            if len(value) > 0:
                if isinstance( value, dict):
                    for (key, val) in value.iteritems():
                        if val not in [ missing, None, '']:
                            n = value
                            break

                elif isinstance( value, list) or isinstance( value, tuple ):
                    for val in value:
                        if val not in [ missing, None, '']:
                            n = value
                            break
            if n is missing:
                return self.default

        raise Invalid( self.msg )

    def on_blank( self, context ):
 
        return self.default

class Empty( Blank, Missing ):

    info = s.text.Empty.info
    msg  = s.text.Empty.msg


class Match( Validator ):

    RAW         = 'Match_RAW'
    REGEX       = 'Match_REGEX'
    VALIDATOR   = 'Match_VALIDATOR'

    info = s.text.Match.info
    msg  = s.text.Match.msg

    def __init__(self, required):
        if not isinstance( required, ValidatorBase ):
            if callable(getattr( required, 'match', None )):
                self.type = Match.REGEX
            else:
                self.type = Match.RAW
        else:
            self.type = Match.VALIDATOR

        self.required = required

    def __extra__( self, context):
        if self.type is Match.RAW:
            required = self.required
        elif self.type is Match.REGEX:
            required = self.required.pattern
        elif self.type is Match.VALIDATOR:
            required = self.required.info_get( context )

        return { 'type': self.type, 'required': required }

    def validate(self, context, value):
        if self.type is Match.RAW:
            if value <> self.required:
                raise Invalid( self.msg )
        elif self.type is Match.REGEX:
            if not self.pattern.match(value):
                raise Invalid( self.msg )
        elif self.type is Match.VALIDATOR:
            result = self.required.validate( context, value)
            if result <> value:
                raise Invalid( self.msg )

        return value

class Not( Validator ):

    info = s.text.Not.info
    msg = s.text.Not.msg

    def __init__(self, criteria):
        if not isinstance( criteria, Validator ):
            criteria = Match( criteria )
        self.validator = criteria

    def __extra__(self, context):
        return { 'criteria': self.validator.info_get( context ) }


    def validate(self, context, value ):

        olderr = context.error

        try:
            result = self.validator.validate( context, value)
        except Invalid:
            return value

        if isinstance( result, ValidationState ):
            try:
                result = result.__cascade__( schema_failed )
            except SchemaFailed:
                return value

        raise Invalid ( self.msg )


class __WrapFunctions__( Validator ):

    __validators__ = []

    class __FuncWrap__( object ):

        def __init__( self, validator, wraps ):
            self.validator = validator
            self.wraps = wraps

        def __call__( self, *args, **kwargs ):
            for wrap in self.wraps:
                wrap( *args, **kwargs )

            return self.validator

    def __getattr__( self, key ):
        if not '__function_wraps__' in self.__dict__:
            self.__function_wraps__ = {}

        if key not in self.__function_wraps__:
            wraps = []
            for validator in self.__validators__:
                func = getattr( validator, key, None )
                if callable( func ):
                    wraps.append( func )
            if not wraps:
                return object.__getattribute__( self, key )

            self.__function_wraps__[key] = __WrapFunctions__.__FuncWrap__( self, wraps )

        return self.__function_wraps__[key]

class And( __WrapFunctions__ ):

    def __init__(self, *criteria):

        criteria = list(criteria)
        for pos in range(len(criteria)):
            if not isinstance(criteria[pos], Validator):
                criteria[pos] = Match(criteria[pos])

        self.__validators__ = criteria
        self.msg = None
        self.info = None

    def __extra__( self, context):
        criteria = []

        for validator in self.__validators__:
            criteria.append(validator.info_get(context) )

        return { 'criteria': criteria }

    def validate(self, context, value ):

        result = value
        for validator in self.__validators__:
            try:
                result = validator.validate(context, result)
            except Invalid,e:
                if not self.info:
                    e[0].update( validator.info_get( context ) )
                else:
                    e[0].update( self.info_get( context ) )
                raise e

            if isinstance( result, ValidationState ):
                res, failed = result.__cascade__( )
                if failed:
#                    return value
                    raise Invalid( self.msg )

        return result

class Or( __WrapFunctions__):

    info = s.text.Or.info
    msg  = s.text.Or.msg

    def __init__(self, *criteria ):
        criteria = list(criteria)
        for pos in range(len(criteria)):
            if not isinstance(criteria[pos], ValidatorBase):
                criteria[pos] = Match(criteria[pos])

        self.__validators__ = criteria

    def __extra__(self, context):
        criteria = []

        for validator in self.__validators__:
            criteria.append( validator.info_get(context) )

        return { 'criteria': criteria }

    def validate(self, context, value):

        if value is IGNORE:
            value = context.value

        errors = []
        lasterr = None

        for validator in self.__validators__:
            if  isinstance( validator, SchemaBase ) and not validator.allow_extra_fields \
            and ( isinstance( value, dict ) or ( isinstance( value, list ) and not isinstance( value, str ) ) ):

                field_index = validator.field_index_get( context )
                values = {}

                for field in field_index:
                    values[field] = value.get(field, missing)

                value_ = values
            else:
                value_ = value

            try:
                result = validator.validate(context, value_)
            except Invalid, err:
                errors.append( err[0] )
                context.validated = False
                lasterr = err
                lasterr[0].update( validator.info_get( context ) )
                continue

            if isinstance( result, ValidationState ):
                try:
                    result.__cascade__( errback = schema_failed )
                except SchemaFailed:
                    context.validated = False
                    continue

            return result

        if lasterr:
            errors = errors[:-1]
            if errors:
                lasterr[0]['previous_errors'] = errors
            raise lasterr

        raise Invalid( self.msg )


class Call( Validator ):

    def __init__( self, func ):
        self.__func__ = func

    def validate( self, context, value ):
        return self.__func__( context, value )


