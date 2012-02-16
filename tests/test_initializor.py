import os
import errno
import shutil
import unittest

from mock import Mock
from config import config
from initialize import Initializor
from errors.baboon_exception import BaboonException


class TestInitializor(unittest.TestCase):

    def setUp(self):
        config = Mock()
        config.metadir_name = '.baboon'
        self.metadir = "/foopath/%s" % config.metadir_name

    def test_mkdir_success(self):
        """ Tests if the instanciation of the Initializor class works
        """

        raised = False
        os.mkdir = Mock()

        try:
            initializor = Initializor()
            initializor.create_metadir()
        except:
            raised = True

        self.assertEquals(raised, False)

    def test_folder_enoent(self):
        """ Tests for enoent exception
        """

        os.mkdir = Mock()
        os.mkdir.side_effect = OSError(errno.ENOENT,
                                       "No such file or directory",
                                       "/foopath/%s" % config.metadir_name)

        with self.assertRaisesRegexp(BaboonException,
                                     "No such file or directory"):
            initializor = Initializor()
            initializor.create_metadir()

    def test_folder_eexist(self):
        """ Tests if the path already exist
        """

        os.mkdir = Mock()
        os.mkdir.side_effect = OSError(errno.EEXIST,
                                       "File exists",
                                       "/foopath/%s" % config.metadir_name)

        with self.assertRaisesRegexp(BaboonException, 'File exists'):
            initializor = Initializor()
            initializor.create_metadir()

    def test_mkdir_failed(self):
        """ Tests if there's another error raised by os.mkdir
        """

        os.mkdir = Mock()
        os.mkdir.side_effect = OSError(errno.EPERM,
                                       "Operation not permitted"
                                       "/foopath/%s" % config.metadir_name)

        with self.assertRaises(OSError):
            initializor = Initializor()
            initializor.create_metadir()

    def test_walk_and_copy_success(self):
        """ Tests if recursive copy works.
        """

        raised = False
        shutil.copytree = Mock()

        try:
            initializor = Initializor()
            initializor.walk_and_copy()
        except:
            raised = True

        self.assertEquals(raised, False)

    def test_walk_and_copy_failed_shutilerror(self):
        """ Tests if recursive copy fails due to shutil.Error.
        """

        shutil.copytree = Mock()
        shutil.copytree.side_effect = shutil.Error

        with self.assertRaises(BaboonException):
            initializor = Initializor()
            initializor.walk_and_copy()

    def test_walk_and_copy_failed_oserror(self):
        """ Tests if recursive copy fails due to OSError.
        """

        shutil.copytree = Mock()
        shutil.copytree.side_effect = OSError

        with self.assertRaises(BaboonException):
            initializor = Initializor()
            initializor.walk_and_copy()


if __name__ == '__main__':
    unittest.main()
