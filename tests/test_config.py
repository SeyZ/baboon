import os
import unittest

from mock import Mock
from config import Config
from errors.baboon_exception import BaboonException


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.config = Config()

    def test_check_config_success(self):
        """ Tests if the check_config() works"""
        os.path.join = Mock(return_value='/foopath')
        os.path.isdir = Mock(return_value=True)

        ret = self.config.check_config()

        self.assertEquals(ret, True)

    def test_check_config_failure(self):
        """ Tests if a BaboonException is raised when isdir return False
        """
        os.path.join = Mock(return_value='/foopath')
        os.path.isdir = Mock(return_value=False)

        with self.assertRaises(BaboonException):
            ret = self.config.check_config()
            self.assertEquals(ret, None)

    def test_check_config_failure_safe(self):
        """ Tests if there's no BaboonException raised when the safe argument
        is setted to the check_config method
        """
        os.path.join = Mock(return_value='/foopath')
        os.path.isdir = Mock(return_value=False)
        raised = False

        try:
            ret = self.config.check_config(True)
        except:
            raised = True

        self.assertEquals(raised, False)
        self.assertEquals(ret, False)


if __name__ == '__main__':
    unittest.main()
