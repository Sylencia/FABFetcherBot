import praw
import os
import re
import requests
from replit import db

reddit = praw.Reddit(
    client_id = os.environ['client_id'],
    client_secret = os.environ['client_secret'],
    username = os.environ['username'],
    password = os.environ['password'],
    user_agent = "<FABFetcherBot1.0>"
)

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
    self.last_posted = 0
    
    # database exists
    if(len(db) != 0):
      self.last_posted = db["last_posted"]
  
  def find_match(self, comment):
    cards = re.findall(r"\[\[(.*?)\]\]", comment.body)
    msg = ''
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
          if msg != '':
            msg += '\n\n'
          for i, card in enumerate(data):
            print_name = get_print_name(card["name"], card["rarity"], str(card["stats"].get("resource", -1)))
            print_image = card["printings"][0]["image"]
            msg += '[%s](%s)' % (print_name, print_image)
            
            if(i != len(data) - 1):
              msg += '  '
        else:
          print('No cards found')
    
    print(msg)
    self.make_response(msg, comment)

  def make_response(self, msg, comment):
    try:
      comment.reply(msg)
    except Exception as e:
      print(e)

# Setup here
# keep_alive()
bot = FABFetcherBot()
subreddit = reddit.subreddit('FABFetcherBot')
for comment in subreddit.stream.comments(skip_existing=True):
    print(comment.body)
    bot.find_match(comment)