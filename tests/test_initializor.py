import os
import errno
import shutil
import unittest

from mock import Mock, patch
from config import config
from initialize import Initializor
from errors.baboon_exception import BaboonException


class TestInitializor(unittest.TestCase):

    def setUp(self):
        config = Mock()
        config.metadir_name = '.baboon'
        self.metadir = "/foopath/%s" % config.metadir_name

    @patch('os.mkdir')
    def test_mkdir_success(self, m_mkdir):
        """ Tests if the instanciation of the Initializor class works
        """

        raised = False
        try:
            initializor = Initializor()
            initializor.create_metadir()
        except:
            raised = True

        self.assertEquals(raised, False)

    @patch('os.mkdir')
    def test_folder_enoent(self, m_mkdir):
        """ Tests for enoent exception
        """
        m_mkdir.side_effect = OSError(errno.ENOENT,
                                      "No such file or directory",
                                      "/foopath/%s" % config.metadir_name)

        with self.assertRaisesRegexp(BaboonException,
                                     "No such file or directory"):
            initializor = Initializor()
            initializor.create_metadir()

    @patch('os.mkdir')
    def test_folder_eexist(self, m_mkdir):
        """ Tests if the path already exist
        """
        m_mkdir.side_effect = OSError(errno.EEXIST,
                                      "File exists",
                                      "/foopath/%s" % config.metadir_name)

        with self.assertRaisesRegexp(BaboonException, 'File exists'):
            initializor = Initializor()
            initializor.create_metadir()

    @patch('os.mkdir')
    def test_mkdir_failed(self, m_mkdir):
        """ Tests if there's another error raised by os.mkdir
        """
        m_mkdir.side_effect = OSError(errno.EPERM,
                                      "Operation not permitted"
                                      "/foopath/%s" % config.metadir_name)

        with self.assertRaises(OSError):
            initializor = Initializor()
            initializor.create_metadir()

    @patch('shutil.copytree')
    def test_walk_and_copy_success(self, m_copytree):
        """ Tests if recursive copy works.
        """

        raised = False
        try:
            initializor = Initializor()
            initializor.walk_and_copy()
        except:
            raised = True

        self.assertEquals(raised, False)

    @patch('shutil.copytree')
    def test_walk_and_copy_failed_shutilerror(self, m_copytree):
        """ Tests if recursive copy fails due to shutil.Error.
        """
        m_copytree.side_effect = shutil.Error

        with self.assertRaises(BaboonException):
            initializor = Initializor()
            initializor.walk_and_copy()

    @patch('shutil.copytree')
    def test_walk_and_copy_failed_oserror(self, m_copytree):
        """ Tests if recursive copy fails due to OSError.
        """
        m_copytree.side_effect = OSError

        with self.assertRaises(BaboonException):
            initializor = Initializor()
            initializor.walk_and_copy()

    @patch('shutil.copytree')
    def test_walk_and_copy_ignore(self, m_copytree):
        """ Tests if the ignore
        """
        initializor = Initializor()
        initializor.walk_and_copy()

        # gets the lambda ignore fct from copytree()
        ignore_fct = m_copytree.call_args[1]['ignore']

        # calls the ignore fct with static values
        result = ignore_fct('dirname/', ['aaa.txt',
                                         'bbb.txt',
                                         '.ccc.txt',
                                         'ddd.txt',
                                         '.eee.txt',
                                         'fff.txt'])

        # gets the hidden files
        hiddens = [hidden for hidden in result
                   if hidden.startswith('.')]

        # ensures the number of hidden files is correct
        self.assertEquals(len(hiddens), 2)


if __name__ == '__main__':
    unittest.main()
