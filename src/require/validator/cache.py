from .core import ValidatorBase
from ..lib import MISSING, PASS

class CacheBase( ValidatorBase ):

    def __init__( self, result=None, value=None ):
        if not (result and value):
            raise SyntaxError("You need to specify at least either result='location' or value='location'")

    def getCache( self ):
        cache = getattr( context.root, 'cache', None)

        if cache is None:
            cache = context.root.cache = {}

        return cache

class Save( CacheBase ):

    def validate( contex, value ):

        cache = self.getCache()
        if result:
            cache['result'][result] = value
        if value:
            cache['value'][value] = context.get('value',context.__value__)

        return PASS


class Restore( CacheBase ):

    def validate( contex, value ):
        cache = self.getCache()

        if result:
            return cache['result'].get(result,PASS)
        if value:
            context['value'] = cache['value'].get('value',context.__value__)

        return PASS


