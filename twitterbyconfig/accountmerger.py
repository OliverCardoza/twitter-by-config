import enum
import twitter

from twitterbyconfig.models import (
    TwitterUser,
    TwitterList,
    MetaList,
    TwitterAccount,
)


class DiffAction(enum.Enum):
  UNKNOWN = 0
  ACCEPT_ALL = 1
  DO_NOTHING = 2
  CONFIRM_EACH = 3


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
    self._PromptThenMaybeExecute(
        items=follows_to_add,
        summary='Merging follows will result in {0} follows added'.format(
            len(follows_to_add)),
        per_item_desc=lambda item: '    Follow: @{0}'.format(item),
        per_item_executor=lambda item: self._AddFollow(item))
    # Step 3: Removing unnecessary follows.
    follows_to_remove = api_set.difference(config_set)
    self._PromptThenMaybeExecute(
        items=follows_to_remove,
        summary='Merging follows will result in {0} follows removed'.format(
            len(follows_to_remove)),
        per_item_desc=lambda item: '    Unfollow: @{0}'.format(item),
        per_item_executor=lambda item: self._Unfollow(item))

  def _AddFollow(self, follow):
    try:
      self.api.CreateFriendship(screen_name=follow)
    except twitter.TwitterError as e:
      print('   Error adding @{0}: {1}'.format(follow, e))

  def _Unfollow(self, follow):
    self.api.DestroyFriendship(screen_name=follow)

  def _MergeLists(self, api_lists, config_lists):
    # Step 1: Compute list sets.
    api_set = {l.name for l in api_lists}
    config_set = {l.name for l in config_lists}
    canonical_lists = {l.name:l for l in api_lists}
    # Step 2: Create missing lists.
    lists_to_add = config_set.difference(api_set)
    self._PromptThenMaybeExecute(
        items=lists_to_add,
        summary='Merging lists will result in {0} lists created'.format(
            len(lists_to_add)),
        per_item_desc=lambda item: '    Create list: {0}'.format(item),
        per_item_executor=lambda item: self._AddList(item,
                                                     config_lists,
                                                     canonical_lists))
    # Step 3: Remove unnecessary ilsts.
    lists_to_remove = api_set.difference(config_set)
    self._PromptThenMaybeExecute(
        items=lists_to_remove,
        summary='Merging lists will result in {0} lists deleted'.format(
            len(lists_to_remove)),
        per_item_desc=lambda item: '    Delete list: {0}'.format(item),
        per_item_executor=lambda item: self._DeleteList(item,
                                                        api_lists,
                                                        canonical_lists))
    # Step 4: Update list privacy.
    # TODO: list.is_private merge
    # Step 5: Update members for each canonical list.
    for canonical_list in canonical_lists.values():
      config_list = next((l for l in config_lists
                          if l.name == canonical_list.name),
                         None)
      if config_list:
        # Reaching here means that a canonical list (exists in Twitter)
        # has a matching config entry and to perform member merging.
        # Not all config_lists will be merged if it was not created early
        # (maybe via negative prompt answer).
        new_members = self._MergeList(canonical_list,
                                      config_list)
        canonical_lists[config_list.name].members = new_members
    return canonical_lists.values()

  def _AddList(self, list_name, config_lists, canonical_lists):
    config_list = next(l for l in config_lists if l.name == list_name)
    mode = 'private' if config_list.is_private else 'public'
    new_list = self.api.CreateList(config_list.name, mode=mode)
    canonical_lists[new_list.name] = new_list
    return TwitterList.FromPythonTwitter(new_list, [])

  def _DeleteList(self, list_name, api_lists, canonical_lists):
    api_list = next(l for l in api_lists if l.name == list_name)
    self.api.DestroyList(list_id=api_list.id)
    del canonical_lists[api_list.name]
    return api_list

  def _MergeList(self, api_list, config_list):
    # Step 1: Compute member sets.
    api_members = {user.username for user in api_list.members}
    config_members = {user.username for user in config_list.members}
    canonical_members = {user.username:user for user in api_list.members}
    # Step 2: Add missing members.
    members_to_add = config_members.difference(api_members)
    self._PromptThenMaybeExecute(
        items=members_to_add,
        summary='Merging list "{0}" will result in {1} members added'.format(
            config_list.name, len(members_to_add)),
        per_item_desc=lambda item: '    Add @{0} to list "{1}"'.format(
            item, config_list.name),
        per_item_executor=lambda item: self._AddListMember(api_list,
                                                           item,
                                                           canonical_members))
    # Step 3: Remove unnecessary members.
    members_to_remove = api_members.difference(config_members)
    self._PromptThenMaybeExecute(
        items=members_to_remove,
        summary='Merging list "{0}" will result in {1} members removed'.format(
            config_list.name, len(members_to_remove)),
        per_item_desc=lambda item: '    Remove @{0} from list "{1}"'.format(
            item, config_list.name),
        per_item_executor=lambda item: self._RemoveListMember(api_list,
                                                              item,
                                                              canonical_members))
    return canonical_members.values()

  def _AddListMember(self, api_list, member, canonical_members):
    try:
      self.api.CreateListsMember(list_id=api_list.id, screen_name=member)
      canonical_members[member] = TwitterUser(username=member)
    except twitter.TwitterError as e:
      print('   Error add list member @{0}: {1}'.format(member, e))

  def _RemoveListMember(self, api_list, member, canonical_members):
    self.api.DestroyListsMember(list_id=api_list.id, screen_name=member)
    del canonical_members[member]

  def _MergeMetaLists(self, api_ml, config_ml, canonical_lists):
    # Step 1: Hydrate each MetaList into a corresponding TwitterList.
    api_lists = [meta_list.ToTwitterList(canonical_lists)
                 for meta_list in api_ml]
    config_lists = [meta_list.ToTwitterList(canonical_lists)
                    for meta_list in config_ml]
    # Step 2: Perform equivalent list merging as done with non-meta lists.
    self._MergeLists(api_lists, config_lists)

  def _DiffPrompt(self):
    prompt = input(
        '    Proceed? Accept all (a), Do nothing (n), Confirm each (c)? ')
    if prompt == 'a':
      return DiffAction.ACCEPT_ALL
    elif prompt == 'n':
      return DiffAction.DO_NOTHING
    elif prompt == 'c':
      return DiffAction.CONFIRM_EACH
    else:
      return DiffAction.UNKNOWN

  def _PromptThenMaybeExecute(self,
                              items=[],
                              summary='',
                              per_item_desc=lambda item: item,
                              per_item_executor=lambda item: None):
    results = []
    if items:
      print(summary)
      diff_action = self._DiffPrompt()
      if (diff_action == DiffAction.ACCEPT_ALL or
          diff_action == DiffAction.CONFIRM_EACH):
        for item in items:
          print(per_item_desc(item))
          if (diff_action == DiffAction.ACCEPT_ALL or
              (diff_action == DiffAction.CONFIRM_EACH and
               input('      Confirm y/n: ') == 'y')):
            results.append(per_item_executor(item))
    return results
