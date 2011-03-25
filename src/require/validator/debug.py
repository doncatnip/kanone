from .core import ValidatorBase

class Print( ValidatorBase ):

    def __init__( self, result=None, value=None):
        self.result=result
        self.value=value

    def validate( self, context, value):
        if self.result:
            print ("%s - result: %s" % (self.result, value))
        if self.value:
            print ("%s - value: %s" % (self.value, context.get('value',context.__value__)))
        return value
