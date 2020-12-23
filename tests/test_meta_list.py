import unittest
import twitterbyconfig as tbc


class TestMetaList(unittest.TestCase):

  def test_ToConfigDict(self):
    user1 = tbc.TwitterUser(id=1, username='JustinTrudeau')
    user2 = tbc.TwitterUser(id=2, username='BarackObama')
    tl = tbc.TwitterList(id=10,
                         name='META: Politics',
                         is_private=True,
                         members=[user1, user2])
    ml = tbc.MetaList(name='META: Politics',
                      is_private=True,
                      lists=['Canadian Politics', 'US Politics'],
                      twitter_list=tl)
    expected_dict = {
      'name': 'META: Politics',
      'is_private': True,
      'lists': ['Canadian Politics', 'US Politics'],
    }
    self.assertEqual(ml.ToConfigDict(), expected_dict)

  def test_ToConfigDict_FailsWhenNotMetaListName(self):
    ml = tbc.MetaList(name='Politics',
                      is_private=True,
                      lists=['Canadian Politics', 'US Politics'])
    with self.assertRaises(ValueError) as e:
      ml.ToConfigDict()

  def test_ToConfigDict_FailsWhenNoLists(self):
    ml = tbc.MetaList(name='META: Politics',
                      is_private=True,
                      lists=[])
    with self.assertRaises(ValueError) as e:
      ml.ToConfigDict()

  def test_FromConfigDict(self):
    config_dict = {
      'name': 'META: Politics',
      'is_private': True,
      'lists': ['Canadian Politics', 'US Politics'],
    }
    ml = tbc.MetaList.FromConfigDict(config_dict)
    self.assertEqual(ml.name, 'META: Politics')
    self.assertTrue(ml.is_private)
    self.assertCountEqual(ml.lists, config_dict['lists'])

  def test_FromConfigDict_FailsWhenNotMetaList(self):
    config_dict = {
      'name': 'Politics',
      'is_private': True,
      'lists': ['Canadian Politics', 'US Politics'],
    }
    with self.assertRaises(ValueError) as e:
      tbc.MetaList.FromConfigDict(config_dict)

  def test_FromConfigDict_FailsWhenNoLists(self):
    config_dict = {
      'name': 'META: Politics',
      'is_private': True,
      'lists': [],
    }
    with self.assertRaises(ValueError) as e:
      tbc.MetaList.FromConfigDict(config_dict)

  def test_FromTwitterList(self):
    user1 = tbc.TwitterUser(id=1, username='JustinTrudeau')
    user2 = tbc.TwitterUser(id=2, username='BarackObama')
    tl = tbc.TwitterList(id=10,
                         name='META: Politics',
                         is_private=True,
                         members=[user1, user2])
    ml = tbc.MetaList.FromTwitterList(tl)
    self.assertEqual(ml.name, 'META: Politics')
    self.assertTrue(ml.is_private)
    self.assertEqual(ml.lists, None)
    self.assertEqual(ml.twitter_list, tl)

  def test_IsMetaList(self):
    # Valid meta-list names.
    self.assertTrue(tbc.MetaList.IsMetaList('META: Politics'))
    self.assertTrue(tbc.MetaList.IsMetaList('META Art'))
    self.assertTrue(tbc.MetaList.IsMetaList('META - Video Games'))
    self.assertTrue(tbc.MetaList.IsMetaList('META_Finance_and_Crypto'))
    self.assertTrue(tbc.MetaList.IsMetaList('METALICA'))
    # Invalid meta-list names.
    self.assertFalse(tbc.MetaList.IsMetaList('meta politics'))
    self.assertFalse(tbc.MetaList.IsMetaList('politics'))

  def test_ToTwitterList_FromTwitterList(self):
    user1 = tbc.TwitterUser(id=1, username='JustinTrudeau')
    user2 = tbc.TwitterUser(id=2, username='BarackObama')
    tl = tbc.TwitterList(id=10,
                         name='META: Politics',
                         is_private=True,
                         members=[user1, user2])
    ml = tbc.MetaList.FromTwitterList(tl)
    self.assertEqual(ml.ToTwitterList([]), tl)

  def test_ToTwitterList_SimpleJoin(self):
    user1 = tbc.TwitterUser(id=1, username='JustinTrudeau')
    user2 = tbc.TwitterUser(id=2, username='BarackObama')
    list1 = tbc.TwitterList(id=10,
                            name='Canadian Politics',
                            is_private=True,
                            members=[user1])
    list2 = tbc.TwitterList(id=20,
                            name='US Politics',
                            is_private=True,
                            members=[user2])
    expected_list = tbc.TwitterList(name='META: Politics',
                                    is_private=True,
                                    members=[user1, user2])
    ml = tbc.MetaList(name='META: Politics',
                      is_private=True,
                      lists=['Canadian Politics', 'US Politics'])
    tl = ml.ToTwitterList([list1, list2])
    self.assertEqual(tl.name, expected_list.name)
    self.assertEqual(tl.is_private, expected_list.is_private)
    self.assertCountEqual(tl.members, expected_list.members)

  def test_ToTwitterList_ComplexJoin(self):
    user1 = tbc.TwitterUser(id=1, username='user1')
    user2 = tbc.TwitterUser(id=2, username='user2')
    user3 = tbc.TwitterUser(id=3, username='user3')
    user4 = tbc.TwitterUser(id=4, username='user4')
    list1 = tbc.TwitterList(id=10,
                            name='list1',
                            members=[user1, user2])
    list2 = tbc.TwitterList(id=20,
                            name='list2',
                            members=[user2, user3])
    list3 = tbc.TwitterList(id=30,
                            name='list3',
                            members=[user1, user4])
    canonical_lists = [list1, list2, list3] 
    # Create meta-lists.
    ml12 = tbc.MetaList(name='META: 1&2', lists=['list1', 'list2'])
    ml13 = tbc.MetaList(name='META: 1&3', lists=['list1', 'list3'])
    ml23 = tbc.MetaList(name='META: 2&3', lists=['list2', 'list3'])
    # Verify meta-list members after denormalization.
    self.assertCountEqual(ml12.ToTwitterList(canonical_lists).members,
                          [user1, user2, user3])
    self.assertCountEqual(ml13.ToTwitterList(canonical_lists).members,
                          [user1, user2, user4])
    self.assertCountEqual(ml23.ToTwitterList(canonical_lists).members,
                          [user1, user2, user3, user4])


if __name__ == '__main__':
  unittest.main()
