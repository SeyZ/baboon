import jsonpickle
import unittest

from diff_match_patch import diff_match_patch
from mock import MagicMock, patch
from diffman import Diffman


class TestDiffman(unittest.TestCase):

    def setUp(self):
        pass

    def test_diff(self):
        """ Tests if the diff works well
        """

        path1 = '/tmp/file1'
        path2 = '/tmp/file2'
        open_name = 'diffman.open'

        with patch(open_name, create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=file)

            m_file = mock_open.return_value.__enter__.return_value

            reads = ['text1', 'text2']
            m_file.read.side_effect = lambda: reads.pop(0)

            diffman = Diffman()
            json_patch = diffman.diff(path1, path2)
            thepatch = jsonpickle.decode(json_patch)

            differ = diff_match_patch()
            result = differ.patch_apply(thepatch, 'text1')

            self.assertEquals('text2', result[0])

if __name__ == '__main__':
    unittest.main()
