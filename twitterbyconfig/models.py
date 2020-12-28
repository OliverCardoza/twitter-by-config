import dataclasses
import yaml


META_LIST_PREFIX = 'META'


@dataclasses.dataclass
class TwitterUser:
  '''Class representing a Twitter user.
  
  This is the primary object that is part of follow/block/list collections.
  '''
  id: int = None # Optional, may not be present.
  username: str = None

  def ToConfigDict(self):
    return {
      'username': self.username,
    }

  def __eq__(self, other):
    return other and self.username == other.username

  def __hash__(self):
    return hash(self.username)

  @staticmethod
  def FromConfigDict(d):
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

  def ToConfigDict(self):
    sorted_members = sorted(self.members,
                            key=lambda member: member.username.lower())
    return {
      'name': self.name,
      'is_private': self.is_private,
      'members': [member.ToConfigDict() for member in sorted_members],
    }

  @staticmethod
  def FromConfigDict(d):
    if MetaList.IsMetaList(d['name']):
      raise ValueError(
          'Invalid list ({0}) conflicts with meta-list requirements'.format(
              d['name']))
    return TwitterList(id=d.get('id', None),
                       name=d['name'],
                       is_private=d.get('is_private', True),
                       members=[TwitterUser.FromConfigDict(member)
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

  def ToConfigDict(self):
    if not MetaList.IsMetaList(self.name):
      raise ValueError(
          'Invalid meta-list name ({0}), must start with: {1}'.format(
              self.name, META_LIST_PREFIX))
    sorted_lists = sorted(self.lists, key=lambda lst: lst.lower())
    return {
      'name': self.name,
      'is_private': self.is_private,
      'lists': sorted_lists,
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
  def FromConfigDict(d):
    if not MetaList.IsMetaList(d['name']):
      raise ValueError(
          'Invalid meta-list name ({0}), must start with: {1}'.format(
              d['name'], META_LIST_PREFIX))
    if not d['lists']:
      raise ValueError(
          'Importing MetaList FromConfigDict without any lists set.')
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

  def ToConfigDict(self):
    sorted_follows = sorted(self.follows,
                            key=lambda user: user.username.lower())
    sorted_lists = sorted(self.lists,
                          key=lambda lst: lst.name.lower())
    sorted_meta_lists = sorted(self.meta_lists,
                               key=lambda lst: lst.name.lower())
    return {
      'follows': [follow.ToConfigDict() for follow in sorted_follows],
      'lists': [l.ToConfigDict() for l in sorted_lists],
      'meta_lists': [ml.ToConfigDict() for ml in sorted_meta_lists],
    }

  def WriteToConfig(self, config_file):
    with open(config_file, 'w') as stream:
      yaml.dump(self.ToConfigDict(), stream)

  @staticmethod
  def FromConfigDict(d):
    return TwitterAccount(follows=[TwitterUser.FromConfigDict(follow)
                                   for follow in d.get('follows', [])],
                          lists=[TwitterList.FromConfigDict(l)
                                 for l in d.get('lists', [])],
                          meta_lists=[MetaList.FromConfigDict(ml)
                                      for ml in d.get('meta_lists', [])])

  @staticmethod
  def FromApi(twitter_api):
    account = TwitterAccount()
    # Follows
    account.follows = [TwitterUser.FromPythonTwitter(friend)
                       for friend in twitter_api.GetFriends()]
    # Lists and Meta-lists
    account.lists = []
    account.meta_lists = []
    lists = twitter_api.GetLists()
    for l in lists:
      members = twitter_api.GetListMembers(list_id=l.id)
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
        return TwitterAccount.FromConfigDict(yaml.safe_load(stream))
      except yaml.YAMLError as e:
        print('Error reading account data from {0}: {1}'.format(config_file,
                                                                e))
    return None


