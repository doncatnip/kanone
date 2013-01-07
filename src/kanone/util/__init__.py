import inspect

def varargs2kwargs( function, args, kwargs, skipSelf=True ):
    names = getParameterNames( function, skipSelf )

    realargs = list(args)
    shifted = []

    for argpos in range(min(len( names ), len(args))):
        key = names[ argpos ]
        if key in kwargs:
            raise SyntaxError('multiple kw args: %s' % key)
        kwargs[ key ] = args[argpos]
        shifted.append( key )
        del realargs[0]

    return realargs,kwargs,shifted

def getArgSpec( function ):
    function = getattr( function, '__func__', function )
    spec = getattr( function, '__spec__', None)
    if spec is None:
        function.__spec__ = spec = inspect.getargspec( function )
    return spec

def getParameterNames( function, skipSelf=True ):
    function = getattr( function, '__func__', function )
    names = getattr( function, '__parameterNames__', None)
    if names is None:
        spec = getArgSpec( function )
        function.__parameterNames__ = names = skipSelf and spec.args[0] is 'self' and spec.args[1:] or spec.args
    return names

