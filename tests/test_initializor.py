import os
import errno
import unittest

from mock import Mock
from config import config
from initialize import Initializor
from errors.baboon_exception import BaboonException


class TestInitializor(unittest.TestCase):

    def setUp(self):
        config = Mock()
        config.metadir_name = '.baboon'

    def test_success(self):
        """ Tests if the instanciation of the Initializor class works
        """
        os.path.join = Mock(return_value="/foopath/%s" % config.metadir_name)
        os.path.exists = Mock(return_value=False)
        raised = False
        os.mkdir = Mock()

        try:
            initializor = Initializor()
        except:
            raised = True

        self.assertEquals(raised, False)

    def test_folder_enoent(self):
        """ Tests if the path does not exist
        """
        os.path.join = Mock(return_value="/foopath/%s" % config.metadir_name)

        os.mkdir = Mock()
        os.mkdir.side_effect = OSError(errno.ENOENT,
                                       'No such file or directory',
                                       "/foopath/%s" % config.metadir_name)

        with self.assertRaisesRegexp(BaboonException,
                                     'No such file or directory'):
            initializor = Initializor()

    def test_folder_eexist(self):
        """ Tests if the path already exist
        """
        os.path.join = Mock(return_value="/foopath/%s")

        os.mkdir = Mock()
        os.mkdir.side_effect = OSError(errno.EEXIST,
                                       'File exists',
                                       "/foopath/%s" % config.metadir_name)

        with self.assertRaisesRegexp(BaboonException, 'File exists'):
            initializor = Initializor()

    def test_mkdir_failed(self):
        """ Tests if there's another error raised by os.mkdir
        """
        os.path.join = Mock(return_value="/foopath/%s" % config.metadir_name)

        os.mkdir = Mock()
        os.mkdir.side_effect = OSError(errno.EPERM,
                                       'Operation not permitted',
                                       "/foopath/%s" % config.metadir_name)

        with self.assertRaises(OSError):
            initializor = Initializor()


if __name__ == '__main__':
    unittest.main()
