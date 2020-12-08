import dataclasses
import twitter
import yaml


@dataclasses.dataclass
class TwitterUser:
  """Class representing a Twitter user.
  
  This is the primary object that is part of follow/block/list collections.

  Upsync to Twitter:
  - Only name is required.
  """
  id: int = None
  name: str = None


@dataclasses.dataclass
class TwitterList:
  """Class representing a Twitter list.

  Upsync to Twitter:
  - Only name and users are required.
  """
  id: int = None
  name: str = None
  is_private: bool = True
  members: list = None # list[TwitterUser]


@dataclasses.dataclass
class TwitterAccount:
  """Primary model for a Twitter account's configured properties.

  This is the primary model used when pulling current state from Twitter API
  for the purpose of YAML export. It is also the primary model populated from
  a twitter-by-config YAML file for the purpose of updating to Twitter.
  """
  follows: list = None # list[TwitterUser] 
  lists: list = None # list[TwitterList]


def CreateTwitterAccount(api):
  account = TwitterAccount()
  # Follows
  print('populating follows')
  friends = api.GetFriends()
  account.follows = [
      TwitterUser(id=friend.id, name=friend.name)
      for friend in friends]
  # Lists
  print('populating lists')
  account.lists = []
  lists = api.GetLists()
  for l in lists:
    tl = TwitterList()
    tl.id = l.id
    tl.name = l.name
    tl.is_private = l.mode == 'private'
    members = api.GetListMembers(list_id=l.id)
    tl.members = [
      TwitterUser(id=member.id, name=member.name)
      for member in members]
    account.lists.append(tl)
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
    

if __name__ == '__main__':
  api = CreateApi()
  print(api.VerifyCredentials())
  account = CreateTwitterAccount(api)
  print(account)
