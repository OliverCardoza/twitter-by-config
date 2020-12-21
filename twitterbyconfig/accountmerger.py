import twitter

from twitterbyconfig.models import (
    TwitterUser,
    TwitterList,
    MetaList,
    TwitterAccount,
)


class AccountMerger:
  def __init__(self, api):
    self.api = api

  def MergeAccounts(self, api_account, config_account):
    self._MergeFollows(api_account.follows, config_account.follows)
    canonical_lists = self._MergeLists(api_account.lists,
                                       config_account.lists)
    self._MergeMetaLists(api_account.meta_lists,
                         config_account.meta_lists,
                         canonical_lists)

  def _MergeFollows(self, api_follows, config_follows):
    # Step 1: Compute follow sets.
    api_set = {follow.username for follow in api_follows}
    config_set = {follow.username for follow in config_follows}
    # Step 2: Add missing follows.
    follows_to_add = config_set.difference(api_set)
    print('Merging follows will result in {0} follows added'.format(
        len(follows_to_add)))
    if follows_to_add and input('    Proceed? y/n: ') == 'y':
      for follow in follows_to_add:
        print('    Following: @{0}'.format(follow))
        try:
          api.CreateFriendship(screen_name=follow)
        except twitter.TwitterError as e:
          print('   Error adding @{0}: {1}'.format(follow, e))
    # Step 3: Removing unnecessary follows.
    follows_to_remove = api_set.difference(config_set)
    print('Merging follows will result in {0} follows removed'.format(
        len(follows_to_remove)))
    if follows_to_remove and input('    Proceed? y/n: ') == 'y':
      for follow in follows_to_remove:
        print('    Unfollowing: @{0}'.format(follow))
        api.DestroyFriendship(screen_name=follow)

  def _MergeLists(self, api_lists, config_lists):
    # Step 1: Compute list sets.
    api_set = {l.name for l in api_lists}
    config_set = {l.name for l in config_lists}
    canonical_lists = {l.name:l for l in api_lists}
    # Step 2: Create missing lists.
    lists_to_add = config_set.difference(api_set)
    print('Merging lists will result in {0} lists created'.format(
        len(lists_to_add)))
    if lists_to_add and input('    Proceed? y/n: ') == 'y':
      for list_to_add in lists_to_add:
        print('    Adding list: {0}'.format(list_to_add))
        config_list = next(l for l in config_lists if l.name == list_to_add)
        mode = 'private' if config_list.is_private else 'public'
        new_list = api.CreateList(config_list.name, mode=mode)
        canonical_lists[new_list.name] = TwitterList.FromPythonTwitter(new_list, [])
    # Step 3: Remove unnecessary ilsts.
    lists_to_remove = api_set.difference(config_set)
    print('Merging lists will result in {0} lists deleted'.format(
        len(lists_to_remove)))
    if lists_to_remove and input('    Proceed? y/n: ') == 'y':
      for list_to_remove in lists_to_remove:
        print('    Removing list: {0}'.format(list_to_remove))
        api_list = next(l for l in api_lists if l.name == list_to_remove)
        api.DestroyList(list_id=api_list.id)
        del canonical_lists[api_list.name]
    # Step 4: Update list privacy.
    # TODO: list.is_private merge
    # Step 5: Update members for each list.
    for config_list in config_lists:
      new_members = self._MergeList(canonical_lists[config_list.name],
                                    config_list)
      canonical_lists[config_list.name].members = new_members
    return canonical_lists.values()

  def _MergeList(self, api_list, config_list):
    # Step 1: Compute member sets.
    api_members = {user.username for user in api_list.members}
    config_members = {user.username for user in config_list.members}
    canonical_members = {user.username:user for user in api_list.members}
    # Step 2: Add missing members.
    members_to_add = config_members.difference(api_members)
    print('Merging list "{0}" will result in {1} members added'.format(
        config_list.name, len(members_to_add)))
    if members_to_add and input('    Proceed? y/n: ') == 'y':
      for member in members_to_add:
        print('   Adding member to "{0}": @{1}'.format(config_list.name,
                                                       member))
        try:
          api.CreateListsMember(list_id=api_list.id, screen_name=member)
          canonical_members[member] = TwitterUser(username=member)
        except twitter.TwitterError as e:
          print('   Error add list member @{0}: {1}'.format(member, e))
    # Step 3: Remove unnecessary members.
    members_to_remove = api_members.difference(config_members)
    print('Merging list "{0}" will result in {1} members removed'.format(
        config_list.name, len(members_to_remove)))
    if members_to_remove and input('    Proceed? y/n: ') == 'y':
      for member in members_to_remove:
        print('   Removing member from "{0}": @{1}'.format(config_list.name,
                                                           member))
        api.DestroyListsMember(list_id=api_list.id, screen_name=member)
        del canonical_members[member]
    return canonical_members.values()

  def _MergeMetaLists(self, api_ml, config_ml, canonical_lists):
    # Step 1: Hydrate each MetaList into a corresponding TwitterList.
    api_lists = [meta_list.ToTwitterList(canonical_lists)
                 for meta_list in api_ml]
    config_lists = [meta_list.ToTwitterList(canonical_lists)
                    for meta_list in config_ml]
    # Step 2: Perform equivalent list merging as done with non-meta lists.
    self._MergeLists(api_lists, config_lists)

