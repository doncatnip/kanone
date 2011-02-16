from ..lib import messages, MISSING, PASS, ValidatorBase
from ..error import Invalid

from .core import Validator

import re

import logging
log = logging.getLogger(__name__)

class Missing( Validator ):

    messages\
        ( fail='This field must be left out'
        )

    def __init__( self, default = PASS ):
        self.default = default

    def on_value( self, context, value ):
        raise Invalid(  )

    def on_missing( self, context ):
        return self.default

class Blank( Validator ):

    messages\
        ( fail='This field must be blank'
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

        raise Invalid( )

    def on_blank( self, context ):
        return self.default


class Empty( Blank, Missing ):

    messages\
        ( fail='This field must be empty (missing or blank)'
        )


class Match( Validator ):

    messages\
        ( fail='Value must match %(criteria)s'
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

    def appendSubValidators( self, subValidators ):
        if self.type == Match.VALIDATOR:
            self.required.appendSubValidators( subValidators )
            subValidators.append( self.required )

    def on_value(self, context, value ):

        if self.type is Match.REGEX:
            if not self.pattern.match(value):
                raise Invalid( type=self.type, criteria=required.pattern)
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
            raise Invalid(  type=self.type, critaria=compare )

        return PASS

    def on_missing(self, context):
        if self.type is Match.VALIDATOR:
            return self.on_value( self, context, context.value )

    on_blank = on_missing

class Len( Validator ):

    messages\
        ( type="Can not get len from values of type %(type)s"
        , fail="Value must be between %(min)s and %(max)s in length"
        )

    def __init__(self, min=0, max=None, returnLen=False):
        self.min = min
        self.max = max
        self.returnResult = returnLen

    def on_value(self, context, value):
        try:
            result = len(value)
        except Exception,e:
            raise Invalid('type',type=value.__class__.__name__)

        if result<self.min or (self.max is not None and result>self.max )
            raise Invalid('fail',min=self.min, max=self.max)

        if self.returnLen:
            return result
        else:
            return PASS


class In( Validator ):
    messages\
        ( fail="Value must be one of %(required)s"
        )

    def __init__( self, required=[] ):
        self.required = reqiered

    def on_value(self, context, value):
        if not value in selt.required:
            raise Invalid('fail')

        return PASS

