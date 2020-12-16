import argparse
import dataclasses
import twitter
import yaml


META_LIST_PREFIX = 'META'


@dataclasses.dataclass
class TwitterUser:
  '''Class representing a Twitter user.
  
  This is the primary object that is part of follow/block/list collections.
  '''
  id: int = None # Optional, may not be present.
  username: str = None

  def ToDict(self):
    return {
      'username': self.username,
    }

  def __eq__(self, other):
    return other and self.username == other.username

  def __hash__(self):
    return hash(self.username)

  @staticmethod
  def FromDict(d):
    return TwitterUser(id=d.get('id', None), username=d['username'])

  @staticmethod
  def FromPythonTwitter(user):
    return TwitterUser(id=user.id, username=user.screen_name)


@dataclasses.dataclass
class TwitterList:
  '''Class representing a Twitter list.'''
  id: int = None # Optional, may not be present.
  name: str = None
  is_private: bool = True
  members: list = None # list[TwitterUser]

  def ToDict(self):
    return {
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
    # Do not guard against creating TwitterList for MetaList because
    # this class can hold the denormalized MetaList data from Twitter API.
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
  # Only present when read from config.
  lists: list = None # list[str]
  # Only present when read from API.
  twitter_list: TwitterList = None

  def ToDict(self):
    if not MetaList.IsMetaList(self.name):
      raise ValueError(
          'Invalid meta-list name ({0}), must start with: {1}'.format(
              self.name, META_LIST_PREFIX))
    if not self.lists:
      raise ValueError('Exporting MetaList ToDict without any lists set.')
    return {
      'name': self.name,
      'is_private': self.is_private,
      'lists': self.lists,
    }

  def ToTwitterList(self, canonical_lists):
    '''Denormalizes a MetaList into a TwitterList given the canonical TwitterLists.'''
    if self.twitter_list:
      return self.twitter_list
    members = set()
    for canonical_list in canonical_lists:
      if canonical_list.name in self.lists:
        members.update(canonical_list.members)
    return TwitterList(name=self.name,
                       is_private=self.is_private,
                       members=list(members))

  @staticmethod
  def FromDict(d):
    if not MetaList.IsMetaList(d['name']):
      raise ValueError(
          'Invalid meta-list name ({0}), must start with: {1}'.format(
              d['name'], META_LIST_PREFIX))
    if not d['lists']:
      raise ValueError('Importing MetaList FromDict without any lists set.')
    return MetaList(name=d['name'],
                    is_private=d['is_private'],
                    lists=d['lists'])

  @staticmethod
  def FromTwitterList(twitter_list):
    return MetaList(name=twitter_list.name,
                    is_private=twitter_list.is_private,
                    twitter_list=twitter_list)

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
  meta_lists: list = None # list[MetaList]

  def ToDict(self):
    return {
      'follows': [follow.ToDict() for follow in self.follows],
      'lists': [l.ToDict() for l in self.lists],
      'meta_lists': [ml.ToDict() for ml in self.meta_lists],
    }

  def WriteToConfig(self, config_file):
    with open(config_file, 'w') as stream:
      yaml.dump(self.ToDict(), stream)

  @staticmethod
  def FromDict(d):
    return TwitterAccount(follows=[TwitterUser.FromDict(follow)
                                   for follow in d.get('follows', [])],
                          lists=[TwitterList.FromDict(l)
                                 for l in d.get('lists', [])],
                          meta_lists=[MetaList.FromDict(ml)
                                      for ml in d.get('meta_lists', [])])

  @staticmethod
  def FromApi(api):
    account = TwitterAccount()
    # Follows
    account.follows = [TwitterUser.FromPythonTwitter(friend)
                       for friend in api.GetFriends()]
    # Lists and Meta-lists
    account.lists = []
    account.meta_lists = []
    lists = api.GetLists()
    for l in lists:
      members = api.GetListMembers(list_id=l.id)
      twitter_list = TwitterList.FromPythonTwitter(l, members)
      if MetaList.IsMetaList(l.name):
        account.meta_lists.append(MetaList.FromTwitterList(twitter_list))
      else:
        account.lists.append(twitter_list)
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
    canonical_lists = self._MergeLists(api_account.lists,
                                       config_account.lists,
                                       destructive)
    self._MergeMetaLists(api_account.meta_lists,
                         config_account.meta_lists,
                         canonical_lists,
                         destructive)

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
    # TODO: list.is_private merge
    for api_list in api_lists:
      if not destructive or api_list.name in config_set:
        canonical_lists[api_list.name] = api_list
    for config_list in config_lists:
      canonical_lists[config_list.name].members = (
          self._MergeList(canonical_lists[config_list.name],
                          config_list,
                          destructive))
    return canonical_lists.values()

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
    canonical_members = {}
    for api_member in api_list.members:
      if not destructive or api_member.username in config_members:
        canonical_members[api_member.username] = api_member
    if not members_to_add and not members_to_remove:
      # No changes will occurso skip confirmation.
      return canonical_members.values()
    if input('    Proceed? y/n: ') == 'y':
      for member in members_to_add:
        print('   Adding member to "{0}": @{1}'.format(config_list.name,
                                                       member))
        try:
          api.CreateListsMember(list_id=api_list.id, screen_name=member)
          canonical_members[member] = TwitterUser(username=member)
        except twitter.TwitterError as e:
          print('   Error add list member @{0}: {1}'.format(member, e))
      for member in members_to_remove:
        print('   Removing member from "{0}": @{1}'.format(config_list.name,
                                                           member))
        api.DestroyListsMember(list_id=api_list.id, screen_name=member)
    return canonical_members.values()

  def _MergeMetaLists(self, api_ml, config_ml, canonical_lists, destructive):
    # Step 1: Hydrate each MetaList into a corresponding TwitterList.
    api_lists = [meta_list.ToTwitterList(canonical_lists)
                 for meta_list in api_ml]
    config_lists = [meta_list.ToTwitterList(canonical_lists)
                    for meta_list in config_ml]
    # Step 2: Perform equivalent list merging as done with non-meta lists.
    self._MergeLists(api_lists, config_lists, destructive)


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
    account_merger.MergeAccounts(
        api_account, config_account, destructive=args.destructive_upload)
  else:
    raise ValueError('Unsupported operation: {0}'.format(args.operation))
