import unittest
import twitterbyconfig as tbc

class Test(unittest.TestCase):

  def test_ToConfigDict(self):
    tu_dict = tbc.TwitterUser(id=1, username='Twitter').ToConfigDict()
    self.assertEqual(tu_dict, {'username': 'Twitter'})

if __name__ == '__main__':
  unittest.main()
