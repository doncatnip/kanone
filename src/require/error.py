class Invalid(Exception):

    def __init__(self, msg, **kwargs):
        kwargs = self.parse(kwargs)
        kwargs['msg'] = msg
        Exception.__init__(self, kwargs)

    @staticmethod
    def parse(kwargs):
        ret = dict(kwargs)
        if 'extra' in ret:
            _extra = ret.pop('extra')
            for (key, value) in _extra.iteritems():
                ret[key] = value

        return ret

class DepencyError(Invalid):
    pass

class IsMissing(Invalid):
    pass
