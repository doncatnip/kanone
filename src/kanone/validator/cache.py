from .core import ValidatorBase
from ..lib import Invalid, MISSING

class CacheBase( ValidatorBase ):

    def getCache( self, context, isGlobal=False ):
        if isGlobal:
            context = context.root

        cache = getattr( context, 'cache', None)

        if cache is None:
            cache = context.cache = {}

        return cache

class Set( CacheBase ):

    def __init__( self, key, value=MISSING ):
        self.key = key
        self.value = value

    def validate( self, context, value ):

        cache = self.getCache( context )
        val = value
        if self.value is not MISSING:
            val = self.value
        cache[self.key] = val

        return value

class Get( CacheBase ):
    def __init__( self, key ):
        self.key = key

    def validate( self, context, value ):
        cache = self.getCache( context )
        result = cache.get(self.key, MISSING)
        if result is MISSING:
            raise Invalid( value, self )

        return result


