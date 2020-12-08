This project aims to help configure your Twitter account using a plaintext
config file.

You write your own config and then use the tool to configure your accounts
follow list, block list, Twitter lists based on the source.

## Install

```
sudo apt-get install python3 python3-pip
pip3 install python-twitter pyyaml
```

## WIP

So far can import some basic data and print to console:

```
python3 main.py
```

TODO

*  import from Twitter to create YAML
*  build model from YAML
*  compare model built from YAML to Twitter source
*  perform inserts to TwitterApi to make it superset of YAML
*  conditionally perform deletes to TwitterApi to make it consistent with YAML
