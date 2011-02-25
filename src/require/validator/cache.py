from .core import ValidatorBase
from ..lib import MISSING, PASS

class CacheBase( ValidatorBase ):

    def __init__( self, result=None, value=None ):
        if not (result or value):
            raise SyntaxError("You need to specify at least either result='location' or value='location'")
        self.result = result
        self.value = value

    def getCache( self, context ):
        cache = getattr( context.root, 'cache', None)

        if cache is None:
            cache = context.root.cache = {}
            cache['result'] = {}
            cache['value'] = {}

        return cache

class Save( CacheBase ):

    def validate( self, context, value ):

        cache = self.getCache( context )
        if self.result:
            cache['result'][self.result] = value
        if self.value:
            cache['value'][self.value] = context.get('value',context.__value__)

        return value


class Restore( CacheBase ):

    def validate( self, context, value ):
        cache = self.getCache( context )

        if self.result:
            return cache['result'].get(self.result,PASS)
        if self.value:
            context['value'] = cache['value'].get(self.value,context.__value__)

        return value


