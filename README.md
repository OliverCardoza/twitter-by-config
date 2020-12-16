This project aims to help configure your Twitter account using a plaintext
config file.

You write your own config and then use the tool to configure your accounts
follow list, block list, Twitter lists based on the source.

## Install

```
sudo apt-get install python3 python3-pip
pip3 install python-twitter pyyaml
```

## Usage Instructions

### Set up

To use the script you will need to configure a Twitter application to access
the Twitter API. Collecting the varius keys, secrets, and tokens is outlined
on the `python-twitter` documentation here:

https://python-twitter.readthedocs.io/en/latest/getting_started.html

This is a bit of a pain but shouldn't take more than 5 - 10 minutes. Once you
have collected the relevant tokens make a copy of `secrets_example.yaml`
called `secrets.yaml` and copy your keys there:

```
cp secrets_example.yaml secrets.yaml
vim secrets.yaml
```

### Download Account data

Download your account data to a config file, e.g. twitter.yaml

```
python3 main.py download twitter.yaml
```

This is the recommended starting point for your config file by basing it on
pre-existing data you've already configured. Now you can make edits to this
config file and use it to configure your Twitter account by uploading it
as described in the next section.

### Uploading Account config

This process will take your config file as the source-of-truth and make
mutations to your account via the Twitter API. All mutations will outline the
proposed changes and ask for confirmation [y/n] before proceeding.

```
python3 main.py upload twitter.yaml
```

By default this will only make constructive operations (add follows, add lists,
add list members). To enable it to make destructive operations (unfollow,
delete lists, delete list members) you must enable the `--destructive_upload`
flag:

```
python3 main.py --destructive_upload=True upload twitter.yaml 
```

## Caveats

The following are the primary caveats one should think about before using this
script:

*   limited field support (e.g. blocks, list descriptions not yet supported)
*   quirky handling of list name change logic (e.g. old list deleted, new list created)
*   does not gracefully handle @username changes

## New Features

### Meta-lists

A meta-list is a dynamic list composed of other lists. One use case might be if
you would like a catch-all "Gaming" list to be composed of everyone on your
"Starcraft" and "R6 Siege" lists. It would be tedious to have to add a new
follow, for example @SC2ByuN to both "Starcraft" and "Gaming" lists. Instead
this can be accomplished using a meta-list definition:

```
lists:
- name: Starcraft
  is_private: true
  members:
  - username: ENCE_Serral
  - username: LowkoTV
  - username: SC2ByuN
- name: R6 Siege
  is_private: true
  members:
  - username: MacieJayGaming
  - username: DARUSSIANBADGER
meta_lists:
- name: "META: Gaming"
  is_private: true
  lists:
  - Starcraft
  - R6 Siege
```

There are a number of ways I could have implemented nested lists. I chose the
current way for simplicity and ease of implementation.

Requirements:

* meta-list name must start with "META"
* meta-list can only include other lists, no direct members
* meta-lists are ignored during "download" operation

