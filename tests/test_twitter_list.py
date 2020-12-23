import dataclasses
import unittest
import twitterbyconfig as tbc


@dataclasses.dataclass
class PythonTwitterList:
  id: int = None
  name: str = None
  mode: str = None


@dataclasses.dataclass
class PythonTwitterUser:
  id: int = None
  screen_name: str = None


class TestTwitterList(unittest.TestCase):

  def test_ToConfigDict(self):
    user1 = tbc.TwitterUser(id=1, username='Twitter')
    user2 = tbc.TwitterUser(id=2, username='Facebook')
    tl = tbc.TwitterList(id=10,
                         name='Social Media',
                         is_private=True,
                         members=[user1, user2])
    expected_dict = {
      'name': 'Social Media',
      'is_private': True,
      'members': [{'username': 'Twitter'}, {'username': 'Facebook'}],
    }
    self.assertEqual(tl.ToConfigDict(), expected_dict)

  def test_FromConfigDict(self):
    config_dict = {
      'name': 'Social Media',
      'is_private': True,
      'members': [{'username': 'Twitter'}, {'username': 'Facebook'}],
    }
    tl = tbc.TwitterList.FromConfigDict(config_dict)
    self.assertEqual(tl.id, None)
    self.assertEqual(tl.name, 'Social Media')
    self.assertTrue(tl.is_private)
    self.assertEqual(len(tl.members), 2)
    self.assertEqual(tl.members[0].id, None)
    self.assertEqual(tl.members[0].username, 'Twitter')
    self.assertEqual(tl.members[1].id, None)
    self.assertEqual(tl.members[1].username, 'Facebook')

  def test_FromConfigDict_FailsForMetaList(self):
    config_dict = {
      'name': 'META: Social Media',
      'is_private': True,
      'members': [{'username': 'Twitter'}, {'username': 'Facebook'}],
    }
    with self.assertRaises(ValueError) as e:
      tbc.TwitterList.FromConfigDict(config_dict)

  def test_FromPythonTwitter(self):
    ptl = PythonTwitterList(id=10, name='Social Media', mode='private')
    ptuser1 = PythonTwitterUser(id=1, screen_name='Twitter')
    ptuser2 = PythonTwitterUser(id=2, screen_name='Facebook')
    members = [ptuser1, ptuser2]
    tl = tbc.TwitterList.FromPythonTwitter(ptl, members)
    self.assertEqual(tl.id, 10)
    self.assertEqual(tl.name, 'Social Media')
    self.assertTrue(tl.is_private)
    self.assertEqual(len(tl.members), 2)
    self.assertEqual(tl.members[0].id, 1)
    self.assertEqual(tl.members[0].username, 'Twitter')
    self.assertEqual(tl.members[1].id, 2)
    self.assertEqual(tl.members[1].username, 'Facebook')


if __name__ == '__main__':
  unittest.main()
