from ..lib import PASS, MISSING
from ..error import Invalid

from .core import Validator, ValidatorBase, messages

from copy import copy

import logging, sys

_python3 = sys.version_info[0]>=3

log = logging.getLogger(__name__)


@messages\
    ( fail='This field must be left out'
    )
class Missing( Validator ):

    def setParameters(self, default=PASS ):
        self.default = default

    def on_value( self, context, value ):
        raise Invalid( value, self )

    def on_missing( self, context ):
        if self.default is PASS:
            return MISSING
        return copy(self.default)
@messages\
    ( fail='This field must be blank'
    )
class Blank( Validator ):

    def setParameters( self, default = PASS ):
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
                    for (key, val) in value.items():
                        if val not in [ MISSING, None, '']:
                            n = value
                            break

                elif isinstance( value, list) or isinstance( value, tuple ):
                    for val in value:
                        if val not in [ MISSING, None, '']:
                            n = value
                            break
            if n is MISSING:
                return copy(self.default)

        raise Invalid( value, self )

    def on_blank( self, context, value ):
        if self.default is PASS:
            return value
        return copy(self.default)

@messages\
    ( fail='This field must be empty (missing or blank)'
    )
class Empty( Blank, Missing ):
    pass


@messages\
    ( fail='Value must match %(criterion)s'
    )
class Match( Validator ):

    RAW         = 'Match_RAW'
    REGEX       = 'Match_REGEX'
    VALIDATOR   = 'Match_VALIDATOR'

    def setParameters(self, criterion, ignoreCase=False):
        if not isinstance( criterion, ValidatorBase ):
            if hasattr(getattr( criterion, 'match', None ),'__call__'):
                self.type = Match.REGEX
            else:
                self.type = Match.RAW
        else:
            self.type = Match.VALIDATOR

        self.ignoreCase = ignoreCase
        self.criterion = criterion

    def appendSubValidators( self, subValidators ):
        if self.type == Match.VALIDATOR:
            self.criterion.appendSubValidators( subValidators )
            subValidators.append( self.criterion )

    def on_value(self, context, value ):
        if self.type is Match.REGEX:
            if _python3 and isinstance( value, bytes):
                value = value.decode('utf8')
            if not self.criterion.match(value):
                raise Invalid( value, self, matchType=self.type, criterion=self.criterion.pattern)
            return value
        elif self.type is Match.VALIDATOR:
            try:
                compare = self.criterion.validate( context, value )
            except Invalid as e:
                raise Invalid( value, self, matchType=self.type, criterion=e )
        else:
            compare = self.criterion

        val = value
        if self.ignoreCase:
            compare = str(compare).lower()
            val = str(value).lower()

        if val != compare:
            raise Invalid( value, self, matchType=self.type, criterion=compare )

        return value

    def on_missing(self, context ):
        if self.type is Match.VALIDATOR:
            return self.on_value( context, MISSING )
        return Validator.on_missing( self, context )

    def on_blank(self, context, value ):
        if self.type is Match.VALIDATOR:
            return self.on_value( context, value )
        return Validator.on_blank( self, context, value )


@messages\
    ( type="Can not get len from values of type %(value.type)s"
    , min="Value must have at least %(min)i elements/characters (has %(len)s)"
    , max="Value cannot have more than least %(max)i elements/characters (has %(len)s)"
    )
class Len( Validator ):

    def setParameters(self, min=1, max=None, returnLen=False):
        self.min = min
        self.max = max
        self.returnLen = returnLen

    def on_value(self, context, value):
        try:
            result = len(value)
        except Exception:
            raise Invalid( value, self, 'type' )

        if result<self.min:
            raise Invalid( value, self, 'min', min=self.min, max=self.max, len=result)
        if self.max is not None and result > self.max:
            raise Invalid( value, self, 'max', min=self.min, max=self.max, len=result)

        if self.returnLen:
            return result
        else:
            return value

@messages\
    ( fail="Value must be one of %(criteria)s"
    )
class In( Validator ):

    def setParameters( self, criteria ):
        self.criteria = criteria

    def on_value(self, context, value):
        if not value in self.criteria:
            raise Invalid( value, self, criteria=self.criteria )

        return value


@messages\
    ( fail="Value must lower or equal to %(max)s"
    )
class Max( Validator ):

    def setParameters( self, max ):
        self.max = max

    def on_value(self, context, value):
        if value > self.max:
            raise Invalid( value, self, max=self.max )

        return value



@messages\
    ( fail="Value must greater or equal to %(min)s"
    )
class Min( Validator ):

    def setParameters( self, min ):
        self.min = min

    def on_value(self, context, value):
        if value < self.min:
            raise Invalid( value, self, min=self.min )

        return value


