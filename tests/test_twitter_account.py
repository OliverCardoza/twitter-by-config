import dataclasses
import unittest
import twitter
import twitterbyconfig as tbc

from unittest.mock import MagicMock, call

class TestTwitterAccount(unittest.TestCase):

  def test_ToConfigDict(self):
    user1 = tbc.TwitterUser(id=1, username='Twitter')
    user2 = tbc.TwitterUser(id=2, username='Facebook')
    tl = tbc.TwitterList(id=10,
                         name='Social Media',
                         is_private=True,
                         members=[user1, user2])
    ml = tbc.MetaList(name='META: All',
                      is_private=True,
                      lists=['Social Media'])
    account = tbc.TwitterAccount(follows=[user1],
                                 lists=[tl],
                                 meta_lists=[ml])

    expected_dict = {
      'follows': [{'username': 'Twitter'}],
      'lists': [{
          'name': 'Social Media',
          'is_private': True, 
          'members': [
              {'username': 'Twitter'},
              {'username': 'Facebook'},
          ],
      }],
      'meta_lists': [{
          'name': 'META: All',
          'is_private': True,
          'lists': ['Social Media'],
      }],
    }
    self.assertEqual(account.ToConfigDict(), expected_dict)

  def test_FromConfigDict(self):
    config_dict = {
      'follows': [{'username': 'Twitter'}],
      'lists': [{
          'name': 'Social Media',
          'is_private': True, 
          'members': [
              {'username': 'Twitter'},
              {'username': 'Facebook'},
          ],
      }],
      'meta_lists': [{
          'name': 'META: All',
          'is_private': True,
          'lists': ['Social Media'],
      }],
    }
    # NOTE: that these models don't include ids compared to the ToConfigDict
    # test. This is because ToConfigDict strips the #'s and FromConfigDict
    # output expects no ideas to be present.
    user1 = tbc.TwitterUser(username='Twitter')
    user2 = tbc.TwitterUser(username='Facebook')
    tl = tbc.TwitterList(name='Social Media',
                         is_private=True,
                         members=[user1, user2])
    ml = tbc.MetaList(name='META: All',
                      is_private=True,
                      lists=['Social Media'])
    expected_account = tbc.TwitterAccount(follows=[user1],
                                          lists=[tl],
                                          meta_lists=[ml])
    account = tbc.TwitterAccount.FromConfigDict(config_dict)
    self.assertEqual(account, expected_account)

  def test_FromApi(self):
    mock_api = twitter.Api()
    user1 = twitter.User.NewFromJsonDict({'id': 1, 'screen_name': 'Twitter'})
    user2 = twitter.User.NewFromJsonDict(
        {'id': 2, 'screen_name': 'BarackObama'})
    mock_api.GetFriends = MagicMock(return_value=[user1])
    list1 = twitter.List.NewFromJsonDict(
        {'id': 10, 'name': 'Social Media', 'mode': 'private'})
    list2 = twitter.List.NewFromJsonDict(
        {'id': 20, 'name': 'META: All', 'mode': 'private'})
    mock_api.GetLists = MagicMock(return_value=[list1, list2])
    mock_api.GetListMembers = MagicMock()
    mock_api.GetListMembers.side_effect = [[user1], [user1, user2]]
    account = tbc.TwitterAccount.FromApi(mock_api)
    # Verify correct mock calls.
    mock_api.GetFriends.assert_called_once()
    mock_api.GetLists.assert_called_once()
    mock_api.GetListMembers.assert_has_calls([call(list_id=10),
                                              call(list_id=20)])
    # Verify correct account is created.
    self.assertEqual(len(account.follows), 1)
    self.assertEqual(account.follows[0].id, 1)
    self.assertEqual(account.follows[0].username, 'Twitter')
    self.assertEqual(len(account.lists), 1)
    self.assertEqual(account.lists[0].id, 10)
    self.assertEqual(account.lists[0].name, 'Social Media')
    self.assertEqual(account.lists[0].is_private, True)
    self.assertEqual(len(account.lists[0].members), 1)
    self.assertEqual(account.lists[0].members[0].id, 1)
    self.assertEqual(account.lists[0].members[0].username, 'Twitter')
    self.assertEqual(len(account.meta_lists), 1)
    self.assertEqual(account.meta_lists[0].name, 'META: All')
    self.assertEqual(account.meta_lists[0].is_private, True)
    self.assertEqual(account.meta_lists[0].twitter_list.id, 20)

  def test_ReadFromConfig(self):
    account = tbc.TwitterAccount.ReadFromConfig('testdata/simple_account.yaml')
    self.assertEqual(len(account.follows), 2)
    self.assertEqual(account.follows[0].username, 'nntaleb')
    self.assertEqual(account.follows[1].username, 'ENCE_Serral')
    self.assertEqual(len(account.lists), 2)
    self.assertEqual(account.lists[0].name, 'Starcraft')
    self.assertEqual(len(account.lists[0].members), 2)
    self.assertEqual(account.lists[0].members[0].username, 'ENCE_Serral')
    self.assertEqual(account.lists[0].members[1].username, 'ESLSC2')
    self.assertEqual(account.lists[1].name, 'Philosophy')
    self.assertEqual(len(account.lists[1].members), 2)
    self.assertEqual(account.lists[1].members[0].username, 'nntaleb')
    self.assertEqual(account.lists[1].members[1].username, 'Naval')
    self.assertEqual(len(account.meta_lists), 1)
    self.assertEqual(account.meta_lists[0].name, 'META: All')
    self.assertEqual(len(account.meta_lists[0].lists), 2)
    self.assertCountEqual(account.meta_lists[0].lists,
                          ['Starcraft', 'Philosophy'])


if __name__ == '__main__':
  unittest.main()
