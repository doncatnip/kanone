from ..lib import pre_validate, missing, IGNORE, ValidationState, ValidatorBase, SchemaBase
from ..error import *
from .. import settings as s

import re, copy

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

    def on_missing(self, context):
        raise Invalid( Validator.msg[0] )

    def on_blank(self, context):
        raise Invalid( Validator.msg[1] )

class Pass( Validator ):

    def on_missing( self, context ):
        return IGNORE

    def on_blank ( self, context):
        return IGNORE


class Empty( Validator ):

    info = s.text.Empty.info
    msg  = s.text.Empty.msg

    def __init__( self, default = IGNORE ):
        self.default = default

    def on_validate( self, context, value ):
        raise Invalid( self.msg )

    def on_blank( self, context ):
        return self.default

    on_missing = on_blank

class Missing( Validator ):

    info = s.text.Missing.info
    msg  = s.text.Missing.msg

    def __init__( self, default = IGNORE ):
        self.default = default

    def on_validate( self, context, value ):
        raise Invalid( self.msg )

    def on_missing( self, context ):
        return self.default

class Blank( Validator ):
    info = s.text.Blank.info
    msg  = s.text.Blank.msg

    def __init__( self, default = IGNORE ):
        self.default = default

    def on_validate( self, context, value):
        raise Invalid( self.msg )

    def on_blank( self, context ):
        return self.default

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

        if type is Match.RAW:
            required = self.required
        elif type is Match.REGEX:
            required = self.required.pattern
        elif type is Match.VALIDATOR:
            required = self.required.info_get( context )

        return { 'type': self.type, 'required': required }

    def on_validate(self, context, value):

        if type is Match.RAW:
            if value <> self.required:
                raise Invalid( self.msg )
        elif type is Match.REGEX:
            if not self.pattern.match(value):
                raise Invalid( self.msg )
        elif type is Match.VALIDATOR:
            olderr = context.error
            result = self.required.do_validate( context, value)
            context.error = olderr
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


    def on_validate(self, context, value=IGNORE):
        if value is IGNORE:
            value = context.value
        if value is IGNORE:
            return value

        olderr = context.error
        context.error = None

        result = self.validator( context, value=value, cascade=False)

        if isinstance( result, ValidationState ):
            try:
                result = result.__cascade__( schema_failed )
            except SchemaFailed:
                pass
            else:
                raise Invalid ( self.msg )

        if not context.error:
            raise Invalid ( self.msg )

        context.error = olderr

        return value

    on_blank = on_missing = on_validate


class And(Validator):

    info = s.text.And.info

    def __init__(self, *criteria):

        criteria = list(criteria)
        for pos in range(len(criteria)):
            if not isinstance(criteria[pos], Validator):
                criteria[pos] = Match(criteria[pos])

        self.__validators__ = criteria
        self.msg = None

    def __extra__( self, context):
        criteria = []

        for validator in self.__validators__:
            criteria.append(validator.info_get(context) )

        return { 'criteria': criteria }

    def on_validate(self, context, value = IGNORE ):
        if value is IGNORE:
            value = context.value
        if value is IGNORE:
            return value

        result = missing

        olderr = context.error
        context.error = None

        result = value

        for validator in self.__validators__:

            result = validator(context, value=result, cascade=False)
 
            if isinstance( result, ValidationState ):
                context.state.abort = True
                try:
                    result.__cascade__( )
                except Invalid,e:
                    raise Invalid( self.msg or e[0]['msg'] )
                finally:
                    context.state.abort = False

            if context.error:
                if self.msg:
                    raise Invalid( self.msg )
                else:
                    raise context.error

        context.error = olderr

        return result

    on_blank = on_missing = on_validate


class Or(Validator):

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

    def on_validate(self, context, value = IGNORE):

        if value is IGNORE:
            value = context.value

        olderr = context.error
        context.error = None

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

            result = validator(context, value=value_, cascade=False)

            if isinstance( result, ValidationState ):
                try:
                    result.__cascade__( errback = schema_failed )
                except SchemaFailed:
                    context.error = None
                    context.validated = False
                    continue

            if context.error:
                context.error = None
                context.validated = False
                continue

            context.error = olderr

            return result

        raise Invalid( self.msg )

    on_blank = on_missing = on_validate


class Call( Validator ):

    def __init__( self, func ):
        self.__func__ = func

    def on_validate( self, context, value=IGNORE ):
        return self.__func__( context, value )

    on_missing = on_blank = on_validate
