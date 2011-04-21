from ..validator.schema import Schema, ForEach
from ..error import Invalid
from ..util import varargs2kwargs, getArgSpec, getParameterNames
from decorator import decorator

import logging

log = logging.getLogger(__name__)

def validate( validator, onInvalid=None ):

    def __validateDecorator( f ):
        spec = getArgSpec( f )

        hasVarargs = spec.varargs is not None
        varargs =  spec.varargs or '*varargs'
        keywords = spec.keywords or None
        parameterNames = tuple(getParameterNames( f, skipSelf=False ))


        def __validateArgs(func, *args, **kwargs):
            (args, kwargs, shifted ) = varargs2kwargs( f, args, kwargs )

            log.debug('parameterNames: %s' % str(parameterNames))
            log.debug('args: %s' % str(args))
            log.debug('kwargs: %s' % str(kwargs))
            log.debug('shifted %s' % str(shifted))

            if keywords is not None:
                restKwargs = dict(\
                    ( key, kwargs.pop(key))\
                        for key in kwargs.keys() if key not in parameterNames
                    )
                kwargs[ keywords ] = restKwargs

            if args or hasVarargs:
                kwargs[ varargs ] = args
            try:
                resultKwargs = validator.context( kwargs ).result
            except Invalid as e:
                if onInvalid is not None:
                    return onInvalid( e )
                else:
                    raise

            if args or hasVarargs:
                resultArgs = resultKwargs.pop( varargs )
                resultArgs = [ resultKwargs.pop(key) for key in shifted  ] + resultArgs
            else:
                resultArgs = []

            if keywords is not None:
                resultKwargs.update( resultKwargs.pop( keywords ) )

            log.debug('resultArgs: %s' % resultArgs)
            log.debug('resultKwargs: %s' % resultKwargs)
            return func( *resultArgs, **resultKwargs )

        return decorator( __validateArgs, f )

    return __validateDecorator

