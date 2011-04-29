from ..validator.schema import Schema, ForEach
from ..error import Invalid
from ..util import varargs2kwargs, getArgSpec, getParameterNames
from decorator import decorator

import logging

log = logging.getLogger(__name__)

class ValidateDecorator:
    def __init__( self, validator, method, skip, onInvalid ):
        self.validator = validator
        self.method = method
        self.onInvalid = onInvalid

        spec = getArgSpec( method )
        hasVarargs = spec.varargs is not None
        varargs =  spec.varargs or '*varargs'
        keywords = spec.keywords or False

        self.methodParameterNames = spec.args
        self.skip = skip or ()
        self.varargs    = varargs

        self.hasVarargs = spec.varargs not in self.skip and hasVarargs
        self.keywords   = keywords not in self.skip and keywords

    def __call__( self, *fargs, **fkwargs):

        (fargs, fkwargs, shifted ) = varargs2kwargs( self.method, fargs, fkwargs )
        origKwargs = dict(fkwargs)

        if self.keywords is not False:
            restKwargs = dict(\
                ( key, fkwargs.pop(key))\
                    for key in fkwargs.keys() if key not in self.methodParameterNames
                )
            fkwargs[ self.keywords ] = restKwargs

        if fargs or self.hasVarargs:
            fkwargs[ self.varargs ] = list(fargs)

        try:
            resultKwargs = self.validator.context\
                ( dict( ( key, fkwargs[ key] ) for key in fkwargs if key not in self.skip ) ).result
        except Invalid as e:
            if self.onInvalid is not None:
                return self.onInvalid( e )
            else:
                raise

        origKwargs.update( resultKwargs )
        resultKwargs = origKwargs

        resultArgs = resultKwargs.pop( self.varargs, fargs )
        resultArgs = [ resultKwargs.pop(key) for key in shifted  ] + resultArgs

        if self.keywords is not False:
            resultKwargs.update( resultKwargs.pop( self.keywords ) )

        return self.method( *resultArgs, **resultKwargs )


def validate( validator, skip=None, onInvalid=None ):
    def __validateDecorator( method ):
        return ValidateDecorator( validator, method, skip, onInvalid)
    return __validateDecorator

"""
def validate( validator, *paramNames, **kwargs ):

    def __validateDecorator( f ):
        spec = getArgSpec( f )

        onInvalid = kwargs.pop( 'onInvalid', None)

        hasVarargs = spec.varargs is not None

        varargs =  spec.varargs or '*varargs'
        keywords = spec.keywords or None

        methodParameterNames = spec.args

        def __validateArgs( *fargs, **fkwargs):
            paramNames = paramNames or methodParameterNames

            keywords = keywords in paramNames and keywords
            hasVarargs = varargs in paramNames and hasVarargs

            (fargs, fkwargs, shifted ) = varargs2kwargs( f, fargs, fkwargs )

            if keywords is not False:
                restKwargs = dict(\
                    ( key, fkwargs.pop(key))\
                        for key in fkwargs.keys() if key not in methodParameterNames
                    )
                fkwargs[ keywords ] = restKwargs

            if fargs or hasVarargs:
                fkwargs[ varargs ] = list(fargs)

            try:
                resultKwargs = validator.context\
                    ( dict( ( key, fkwargs[ key] ) for key in paramNames ) ).result
            except Invalid as e:
                if onInvalid is not None:
                    return onInvalid( e )
                else:
                    raise

            resultArgs = resultKwargs.pop( varargs, fargs )
            resultArgs = [ resultKwargs.pop(key) for key in shifted  ] + resultArgs

            if keywords is not False:
                resultKwargs.update( resultKwargs.pop( keywords ) )
            else:
                resultKwargs.update( restKwargs )

            return f( *resultArgs, **resultKwargs )

        return __validateArgs

    return __validateDecorator
"""
