from .core import ValidatorBase
from ..lib import MISSING, PASS

class CacheBase( ValidatorBase ):

    def __init__( self, result=None, value=None ):
        if not (result or value):
            raise SyntaxError("You need to specify at least either result='location' or value='location'")
        self.result = result
        self.value = value

    def getCache( self, context, isGlobal=False ):
        if isGlobal:
            context = context.root

        cache = getattr( context, 'cache', None)

        if cache is None:
            cache = context.cache = {}

        return cache

class Save( CacheBase ):

    def validate( self, context, value ):

        cache = self.getCache( context )
        if self.result:
            cache[self.result] = value
        if self.value:
            cache[self.value] = context.get('value',context.__value__)

        return value


class Restore( CacheBase ):
    def __init__( self, key ):
        self.key = key

    def validate( self, context, value ):
        cache = self.getCache( context )

        return cache.get(self.key, value)

