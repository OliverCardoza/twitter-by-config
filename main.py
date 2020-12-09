import argparse
import dataclasses
import twitter
import yaml


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
    return TwitterUser(id=d['id'], username=d['username'])

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
    return TwitterList(id=d['id'],
                       name=d['name'],
                       is_private=d['is_private'],
                       members=[TwitterUser.FromDict(member)
                                for member in d['members']])

  @staticmethod
  def FromPythonTwitter(tlist, members):
    return TwitterList(id=tlist.id,
                       name=tlist.name,
                       is_private=(tlist.mode == 'private'),
                       members=[TwitterUser.FromPythonTwitter(member)
                                for member in members])


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

  @staticmethod
  def FromDict(d):
    return TwitterAccount(follows=[TwitterUser.FromDict(follow)
                                   for follow in d['follows']],
                          lists=[TwitterList.FromDict(l)
                                 for l in d['lists']])

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
      members = api.GetListMembers(list_id=l.id)
      account.lists.append(TwitterList.FromPythonTwitter(l, members))
    return account


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
parser.add_argument('operation', type=str, choices=['download'],
                    help=('The operation to perform: \n'
                          '    download: downloads account data from Twitter'
                          ' and outputs to your config file\n'))
parser.add_argument('config_file', type=str, help='The address of your config file.')

if __name__ == '__main__':
  args = parser.parse_args()
  api = CreateApi()
  if args.operation == 'download':
    print('Performing download from TwitterAPI into config file...')
    account = TwitterAccount.FromApi(api)
    with open(args.config_file, 'w') as stream:
      print('Account data downloaded, writing to file...')
      yaml.dump(account.ToDict(), stream)
      print('{0} file updated from TwitterAPI source.'.format(args.config_file))
  else:
    raise ValueError('Unsupported operation: {0}'.format(args.operation))
