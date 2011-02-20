import inspect


class Parameterized( dict ):
    __obj__ = None
    __kwargs__ = None
    __isroot__ = False
    __parent__ = {}

    def __init__( self, objOrParent, args=(), kwargs=None ):
        if kwargs is None:
            kwargs = {}

        if isinstance( objOrParent, Parameterized ):
            newkwargs = dict(objOrParent.__kwargs__ )
            newkwargs.update(kwargs)
            kwargs = newkwargs
            obj = objOrParent.__obj__
            self.__parent__ = objOrParent
        else:
            obj = objOrParent

        self.__obj__ = obj

        for (m,hook) in obj.__parameterizedMethods__:
            setattr( self, m.__name__, Parameterized.__parameterize__( self, m, hook ) )

        if args or kwargs:
            if not hasattr( obj.__init__.im_func, '__spec__'):
                spec = inspect.getargspec( obj.__init__ )
                setattr( obj.__init__.im_func,'__spec__',spec )
            else:
                spec = obj.__init__.__spec__

            realargs = list(args)
            numSpecArgs = len(spec.args )

            for argpos in range( len( args ) ):
                if argpos < numSpecArgs-2:
                    kwargs[ spec.args[ argpos-3 ] ] = args[ argpos ]
                    del realargs[0]

            obj.__init__( self, *realargs, **kwargs )

        self.__kwargs__ = kwargs

    @classmethod
    def __parameterize__( klass, params, m, hook=None ):
        def parameterizedMethod(  *args, **kwargs ):
            theParams = params
            if hook:
                theParams = hook( params, *args, **kwargs )
            return m( theParams, *args, **kwargs )

        return parameterizedMethod

    def __call__( self, *args, **kwargs):
        if args or kwargs:
            return self.clone( *args, **kwargs )
        return self

    def __setattr__(self,key, value):
        if not hasattr(self,key) and not hasattr(value,'__call__'):
            self[key] = value
        else:
            dict.__setattr__( self, key, value )

    def __getattr__(self,key):
        if key in self:
            return self[key]
        if not parent:
            raise AttributeError('Parameter %s not found' % key )
        else:
            return getattr(parent,key)

    def __and__(self,other):
        return self.__dict__['__and__'](other)

    def clone( self, *args, **kwargs):
        return Parameterized( self, args=args, kwargs=kwargs )

    def new( self, *args, **kwargs):
        return Parameterized( self.__obj__, args=args, kwargs=kwargs )


class Parameterize( object ):

    excludeMethods = ['hook','__new__']

    def __new__(klass, *args, **kwargs):
        members = inspect.getmembers( klass )
        methods = []

        for (name,m) in members:
            if name in klass.excludeMethods:
                continue


            if hasattr(m,'im_func'):
                m = m.__get__(klass)

                if name is not '__prepare__':
                    hook = m.im_func.func_dict.get\
                        ( '__parameterizeHook__'
                        , None
                        )
                    if hook is not None:
                        hook = hook.__get__(klass)

                    methods.append\
                        (   ( m
                            , hook
                            )
                        )

                setattr(klass,name,m)

        klass.__parameterizedMethods__ = methods
        klass.__prepare__()

        return Parameterized( klass, args=args, kwargs=kwargs )

    @staticmethod
    def hook(hook):
        def setHook(func):
            func.__parameterizeHook__ = hook
            return func
        return setHook


class Factory:

    _singletons = {}

    def __init__( self, klass ):
        self.klass = klass

    def __call__( self, *args, **kwargs):
        if not self.klass in Factory._singletons:
            obj = self.klass( *args, **kwargs )
            Factory._singletons[ self.klass ] = obj
            return obj
        else:
            obj = Factory._singletons[ self.klass ]

            if isinstance(obj, Parameterized):
                obj = obj( *args, **kwargs)

            return obj




class Validator( Parameterize ):

    def __prepare__( klass ):
        klass.validate = klass.__wrapValidate__( klass.validate )

    def __wrapValidate__( klass,  func ):
        @Parameterize.hook(Validator.prepareParams)
        def validate( *args, **kwargs ):
            try:
                return func( *args, **kwargs)
            except Exception, e:
                print "invalid"

        return validate

    def prepareParams( klass, params, *args, **kwargs ):
        print "prepare"
        return params



@Factory
class SomeValidator( Validator ):

    def __init__( klass, params, param1, param2, param3=False ):
        params.param1 = param1
        params.param2 = param2
        params.param3 = param3

    def validate( klass, params, context, value ):
        print params
        return "42!"

    def __and__( klass, params, other ):
        print "and !"
