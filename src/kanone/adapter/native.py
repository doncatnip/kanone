from ..error import Invalid
from ..util import varargs2kwargs, getArgSpec, getParameterNames

import logging

log = logging.getLogger(__name__)

def validateDecorator( validator, method, include, exclude, onInvalid ):

    if include and exclude:
        raise SyntaxError("'include' and 'exclude' cannot be used at the same time")

    spec = getArgSpec( method )
    hasVarargs = spec.varargs is not None
    varargs =  spec.varargs or '*varargs'
    keywords = spec.keywords or False

    methodParameterNames = getParameterNames( method, skipSelf=False )

    skip = ()
    if exclude:
        skip = exclude
    if include:
        skip = set(methodParameterNames) - set(include)

    varargs    = varargs

    hasVarargs = spec.varargs not in skip and hasVarargs

    keywords   = keywords not in skip and keywords

    def __wrap( *fargs, **fkwargs):

        (fargs, fkwargs, shifted ) = varargs2kwargs( method, fargs, fkwargs, skipSelf=False )
        origKwargs = dict(fkwargs)

        if keywords is not False:
            restKwargs = dict(\
                ( key, fkwargs.pop(key))\
                    for key in list(fkwargs.keys()) if key not in methodParameterNames
                )
            fkwargs[ keywords ] = restKwargs

        if fargs or hasVarargs:
            fkwargs[ varargs ] = list(fargs)

        try:
            resultKwargs =validator.context\
                ( dict( ( key, fkwargs[ key] ) for key in fkwargs if key not in skip ) ).result
        except Invalid as e:
            if onInvalid is not None:
                return onInvalid( e )
            else:
                raise

        origKwargs.update( resultKwargs )

        resultArgs = origKwargs.pop( varargs, fargs )
        resultArgs = [ origKwargs.pop(key) for key in shifted  ] + resultArgs

        if keywords is not False:
            origKwargs.update( origKwargs.pop( keywords ) )

        return method( *resultArgs, **origKwargs )

    return __wrap

def validate( validator, include=None, exclude=None, onInvalid=None ):
    def __createDecorator( method ):
        return validateDecorator( validator, method, include, exclude, onInvalid)
    return __createDecorator

