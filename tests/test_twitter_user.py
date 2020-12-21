import dataclasses
import unittest
import twitterbyconfig as tbc

@dataclasses.dataclass
class PythonTwitterUser:
  id: int = None
  screen_name: str = None


class TestTwitterUser(unittest.TestCase):

  def test_ToConfigDict(self):
    tu_dict = tbc.TwitterUser(id=1, username='Twitter').ToConfigDict()
    self.assertEqual(tu_dict, {'username': 'Twitter'})

  def test_eq(self):
    user1 = tbc.TwitterUser(id=1, username='Twitter')
    user2 = tbc.TwitterUser(id=2, username='Facebook')
    user3 = tbc.TwitterUser(username='Twitter')
    self.assertEqual(user1, user3)
    self.assertNotEqual(user1, user2)
    self.assertNotEqual(user1, None)

  def test_hash(self):
    '''Ensures 2 users with/without ids but same username hash equal.'''
    user1 = tbc.TwitterUser(id=1, username='Twitter')
    user2 = tbc.TwitterUser(id=2, username='Facebook')
    user3 = tbc.TwitterUser(username='Twitter')
    s = {user1}
    self.assertTrue(user1 in s)
    self.assertTrue(user3 in s)
    self.assertFalse(user2 in s)

  def test_FromConfigDict(self):
    user = tbc.TwitterUser.FromConfigDict({'username': 'Twitter'})
    self.assertEqual(user.id, None)
    self.assertEqual(user.username, 'Twitter')

  def test_FromPythonTwitter(self):
    ptu = PythonTwitterUser(id=1, screen_name='Twitter')
    user = tbc.TwitterUser.FromPythonTwitter(ptu)
    self.assertEqual(user.id, 1)
    self.assertEqual(user.username, 'Twitter')


if __name__ == '__main__':
  unittest.main()
