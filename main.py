import argparse
import twitter
import yaml

from twitterbyconfig.models import (
    TwitterUser,
    TwitterList,
    MetaList,
    TwitterAccount,
)

from twitterbyconfig.accountmerger import (
    AccountMerger,
)


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
    account_merger = AccountMerger(api)
    account_merger.MergeAccounts(api_account, config_account)
  else:
    raise ValueError('Unsupported operation: {0}'.format(args.operation))
