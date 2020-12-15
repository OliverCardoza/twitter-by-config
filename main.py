import argparse
import dataclasses
import twitter
import yaml


META_LIST_PREFIX = 'META'


@dataclasses.dataclass
class TwitterUser:
  '''Class representing a Twitter user.
  
  This is the primary object that is part of follow/block/list collections.

  Upsync to Twitter:
  - Only username is required.
  '''
  id: int = None
  username: str = None

  def ToDict(self):
    return {
      'id': self.id,
      'username': self.username,
    }

  @staticmethod
  def FromDict(d):
    return TwitterUser(id=d.get('id', None), username=d['username'])

  @staticmethod
  def FromPythonTwitter(user):
    return TwitterUser(id=user.id, username=user.screen_name)


@dataclasses.dataclass
class TwitterList:
  '''Class representing a Twitter list.

  Upsync to Twitter:
  - Only name and members are required.
  '''
  id: int = None
  name: str = None
  is_private: bool = True
  members: list = None # list[TwitterUser]

  def ToDict(self):
    return {
      'id': self.id,
      'name': self.name,
      'is_private': self.is_private,
      'members': [member.ToDict() for member in self.members],
    }

  @staticmethod
  def FromDict(d):
    if MetaList.IsMetaList(d['name']):
      raise ValueError(
          'Invalid list ({0}) conflicts with meta-list requirements'.format(
              d['name']))
    return TwitterList(id=d.get('id', None),
                       name=d['name'],
                       is_private=d.get('is_private', True),
                       members=[TwitterUser.FromDict(member)
                                for member in d['members']])

  @staticmethod
  def FromPythonTwitter(tlist, members):
    if MetaList.IsMetaList(tlist.name):
      raise ValueError(
          'Invalid list ({0}) conflicts with meta-list requirements'.format(
              tlist.name))
    return TwitterList(id=tlist.id,
                       name=tlist.name,
                       is_private=(tlist.mode == 'private'),
                       members=[TwitterUser.FromPythonTwitter(member)
                                for member in members])


@dataclasses.dataclass
class MetaList:
  '''Class representing a meta-list aka. list of lists.

  This is a new feature not available in Twitter and implemented by the
  twitter-by-config script. For more info see README.md.
  '''
  name: str = None
  is_private: bool = True
  lists: list = None # list[str]

  def ToDict(self):
    if not MetaList.IsMetaList(self.name):
      raise ValueError(
          'Invalid meta-list name ({0}), must start with: {1}'.format(
              self.name, META_LIST_PREFIX))
    return {
      'name': self.name,
      'is_private': self.is_private,
      'lists': self.lists,
    }

  @staticmethod
  def FromDict(d):
    if not MetaList.IsMetaList(d['name']):
      raise ValueError(
          'Invalid meta-list name ({0}), must start with: {1}'.format(
              d['name'], META_LIST_PREFIX))
    return MetaList(name=d['name'],
                    is_private=d['is_private'],
                    lists=d['lists'])

  @staticmethod
  def IsMetaList(name):
    return name.startswith(META_LIST_PREFIX)


@dataclasses.dataclass
class TwitterAccount:
  '''Primary model for a Twitter account's configured properties.

  This is the primary model used when pulling current state from Twitter API
  for the purpose of YAML export. It is also the primary model populated from
  a twitter-by-config YAML file for the purpose of updating to Twitter.
  '''
  follows: list = None # list[TwitterUser] 
  lists: list = None # list[TwitterList]

  def ToDict(self):
    return {
      'follows': [follow.ToDict() for follow in self.follows],
      'lists': [l.ToDict() for l in self.lists],
    }

  def WriteToConfig(self, config_file):
    with open(config_file, 'w') as stream:
      yaml.dump(self.ToDict(), stream)

  @staticmethod
  def FromDict(d):
    return TwitterAccount(follows=[TwitterUser.FromDict(follow)
                                   for follow in d.get('follows', [])],
                          lists=[TwitterList.FromDict(l)
                                 for l in d.get('lists', [])])

  @staticmethod
  def FromApi(api):
    account = TwitterAccount()
    # Follows
    account.follows = [TwitterUser.FromPythonTwitter(friend)
                       for friend in api.GetFriends()]
    # Lists
    account.lists = []
    lists = api.GetLists()
    for l in lists:
      if MetaList.IsMetaList(l.name):
        print('    Skipping import of meta-list: "{0}"'.format(l.name))
        continue
      members = api.GetListMembers(list_id=l.id)
      account.lists.append(TwitterList.FromPythonTwitter(l, members))
    return account

  @staticmethod
  def ReadFromConfig(config_file):
    with open(config_file, 'r') as stream:
      try:
        return TwitterAccount.FromDict(yaml.safe_load(stream))
      except yaml.YAMLError as e:
        print('Error reading account data from {0}: {1}'.format(config_file,
                                                                e))
    return None


class AccountMerger:
  def __init__(self, api):
    self.api = api

  def MergeAccounts(self, api_account, config_account, destructive=False):
    self._MergeFollows(api_account.follows, config_account.follows, destructive)
    self._MergeLists(api_account.lists, config_account.lists, destructive)
    return TwitterAccount.FromApi(api)

  def _MergeFollows(self, api_follows, config_follows, destructive):
    api_set = {follow.username for follow in api_follows}
    config_set = {follow.username for follow in config_follows}
    follows_to_add = config_set.difference(api_set)
    follows_to_remove = api_set.difference(config_set) if destructive else {}
    print('Merging will result in {0} follows added and {1} follows removed.'.format(
        len(follows_to_add), len(follows_to_remove)))
    if not follows_to_add and not follows_to_remove:
      # No changes will occur so skip confirmation.
      return
    if input('    Proceed? y/n: ') == 'y':
      for follow in follows_to_add:
        print('    Following: @{0}'.format(follow))
        try:
          api.CreateFriendship(screen_name=follow)
        except twitter.TwitterError as e:
          print('   Error adding @{0}: {1}'.format(follow, e))
      for follow in follows_to_remove:
        print('    Unfollowing: @{0}'.format(follow))
        api.DestroyFriendship(screen_name=follow)

  def _MergeLists(self, api_lists, config_lists, destructive):
    api_set = {l.name for l in api_lists}
    config_set = {l.name for l in config_lists}
    lists_to_add = config_set.difference(api_set)
    lists_to_remove = api_set.difference(config_set) if destructive else {}
    print('Merging will result in {0} lists added and {1} lists deleted.'.format(
        len(lists_to_add), len(lists_to_remove)))
    canonical_lists = {}
    if lists_to_add or lists_to_remove:
      if input('    Proceed? y/n: ') == 'y':
        for list_to_add in lists_to_add:
          print('    Adding list: {0}'.format(list_to_add))
          config_list = next(l for l in config_lists if l.name == list_to_add)
          mode = 'private' if config_list.is_private else 'public'
          new_list = api.CreateList(config_list.name, mode=mode)
          canonical_lists[new_list.name] = TwitterList.FromPythonTwitter(new_list, [])
        for list_to_remove in lists_to_remove:
          print('    Removing list: {0}'.format(list_to_remove))
          api_list = next(l for l in api_lists if l.name == list_to_remove)
          api.DestroyList(list_id=api_list.id)
    for api_list in api_lists:
      if api_list.name in config_set:
        canonical_lists[api_list.name] = api_list
    for config_list in config_lists:
      self._MergeList(canonical_lists[config_list.name],
                      config_list,
                      destructive)

  def _MergeList(self, api_list, config_list, destructive):
    api_members = {user.username for user in api_list.members}
    config_members = {user.username for user in config_list.members}
    members_to_add = config_members.difference(api_members)
    members_to_remove = (api_members.difference(config_members)
                         if destructive else {})
    print(('Merging list "{0}" will result in {1} members added and {2}'
           ' members removed.').format(config_list.name,
                                       len(members_to_add),
                                       len(members_to_remove)))
    if not members_to_add and not members_to_remove:
      # No changes will occurso skip confirmation.
      return
    if input('    Proceed? y/n: ') == 'y':
      for member in members_to_add:
        print('   Adding member to "{0}": @{1}'.format(config_list.name,
                                                       member))
        try:
          api.CreateListsMember(list_id=api_list.id, screen_name=member)
        except twitter.TwitterError as e:
          print('   Error add list member @{0}: {1}'.format(member, e))
      for member in members_to_remove:
        print('   Removing member from "{0}": @{1}'.format(config_list.name,
                                                           member))
        api.DestroyListsMember(list_id=api_list.id, screen_name=member)


def CreateApi():
  with open('secrets.yaml', 'r') as stream:
    try:
      secrets = yaml.safe_load(stream)
      return twitter.Api(consumer_key=secrets['consumer_key'],
                         consumer_secret=secrets['consumer_secret'],
                         access_token_key=secrets['access_token_key'],
                         access_token_secret=secrets['access_token_secret'])
    except yaml.YAMLError as e:
      print('Error loading secrets.yaml: {0}'.format(e))
  return None
    

parser = argparse.ArgumentParser(
    description='Provides Twitter account management using a plaintext config file.')
parser.add_argument('operation', type=str, choices=['download', 'upload'],
                    help=('The operation to perform: \n'
                          '    download: downloads account data from Twitter'
                          ' and outputs to your config file\n'
                          '    upload: updates account data in Twitter to'
                          ' match your config file\n'))
parser.add_argument('config_file', type=str, help='The address of your config file.')
parser.add_argument('--destructive_upload', type=bool, default=False,
                    help=('When true, upload operation will delete data present'
                          ' in the account from TwitterAPI not present in the'
                          ' config file. This ensures exact consistency between'
                          ' the config file and the account state in Twitter.'))


if __name__ == '__main__':
  args = parser.parse_args()
  api = CreateApi()
  if args.operation == 'download':
    print('Performing download from TwitterAPI into config file...')
    account = TwitterAccount.FromApi(api)
    print('Account data downloaded, writing to file...')
    account.WriteToConfig(args.config_file)
    print('File updated from TwitterAPI source: {0}'.format(args.config_file))
  elif args.operation == 'upload':
    print('Reading account data from config file...')
    config_account = TwitterAccount.ReadFromConfig(args.config_file)
    print('Reading account data from Twitter API...')
    api_account = TwitterAccount.FromApi(api)
    print('Merging account data: destructive? {0}'.format(args.destructive_upload))
    account_merger = AccountMerger(api)
    merged_account = account_merger.MergeAccounts(
        api_account, config_account, destructive=args.destructive_upload)
    if input('Write merged data back to config?'
             ' This will overwrite any local changes y/n: ') == 'y':
      merged_account.WriteToConfig(args.config_file)
      print('Merged account data written to config file.')
  else:
    raise ValueError('Unsupported operation: {0}'.format(args.operation))
