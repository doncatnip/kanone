from form.tests import *

class TestUserdataController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='userdata', action='index'))
        # Test response...
