import praw
import os
import re
import requests
import json

# reddit = praw.Reddit(
#     client_id = os.environ['client_id'],
#     client_secret = os.environ['client_secret'],
#     username = os.environ['username'],
#     password = os.environ['password'],
#     user_agent = "<FABFetcherBot1.0>"
# )

def clean_pitch(pitch):
  pitch_table = {
    'red': '1',
    '1': '1',
    'yellow': '2',
    '2': '2',
    'blue': '3',
    '3': '3',
  }
  return pitch_table.get(pitch, 'all')

def clean_name(name):
  return name.replace(' ', '+').lower()

def get_print_name(name, rarity, pitch):
  pitch_table = {
    '1': 'red',
    '2': 'yellow',
    '3': 'blue'
  }

  if rarity.upper() in ['C', 'R']:
    colour = pitch_table.get(pitch, 'none')
    if colour != 'none':
      return '%s (%s)' % (name, pitch_table[pitch])
    else:
      return name
  else:
    return name


class FABFetcherBot:
  def __init__(self):
    pass

  def can_post(self):
    pass
  
  def find_match(self, comment):
    cards = re.findall(r"\[\[(.*?)\]\]", comment)
    if len(cards) > 0:
      for card in cards:
        raw_name, *raw_pitch = card.split('|')
        raw_pitch = raw_pitch[0] if raw_pitch else 'all'
        pitch = clean_pitch(raw_pitch)
        name = clean_name(raw_name)
        # Request card from fabdb API
        req_kw = 'keywords=%s' % (name)
        req_pitch = '&pitch=%s' % (pitch) if pitch != 'all' else ''
        r = requests.get('https://api.fabdb.net/cards?%s%s' % (req_kw, req_pitch), timeout=10)
        req_json = r.json()
        filtered = filter(lambda n: n.get("name", '').lower() == raw_name.lower(), req_json["data"])
        data = list(filtered)
        total = len(data)
        if total > 0:
          for card in data:
            print_name = get_print_name(card["name"], card["rarity"], str(card["stats"].get("resource", -1)))
            print_image = card["printings"][0]["image"]
            print('[%s](%s)' % (print_name, print_image))
        else:
          print('No cards found')

# Setup here
# keep_alive()
bot = FABFetcherBot()
test = 'Hello [[Snatch]] and [[Command and Conquer|red]]'
bot.find_match(test)
# subreddit = reddit.subreddit('FABFetcherBot')
# for comment in subreddit.stream.comments(skip_existing=True):
#     bot.find_match(comment)