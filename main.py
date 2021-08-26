import praw
import os
import re
import requests
from replit import db

DEBUG = True

reddit = praw.Reddit(
    client_id = os.environ['client_id'],
    client_secret = os.environ['client_secret'],
    username = os.environ['username'],
    password = os.environ['password'],
    user_agent = '<FABFetcherBot1.0>'
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

def get_print_name(name, identifier):
  # strip out non-alphanumeric characters except spaces, then replace spaces with dashes
  check_name = re.sub('[^a-zA-Z0-9 ]', '', name).replace(' ', '-').lower()
  if check_name == identifier:
    return name
  else:
    id_split = identifier.split('-')
    return '%s (%s)' % (name, id_split[-1])

def get_print_card_type(card_talent, card_class, card_type, card_subtype, card_keywords):
  ct = card_type.lower()
  type = ''


  if ct in ['hero', 'equipment', 'action', 'instant', 'mentor', 'resource']:
    if card_talent != None:
      type += '%s ' % (card_talent)
    
    type += '%s %s' % (card_class, card_type)

    if card_subtype != None:
      type += ' - %s' % (card_subtype)
  elif ct in ['attack', 'defense']:
    if card_talent != None:
      type += '%s ' % (card_talent)
    
    type += '%s %s %s' % (card_class, card_type, card_subtype)
  elif ct in ['weapon']:
    if card_talent != None:
      type += '%s ' % (card_talent)
    
    type += '%s %s - %s (%s)' % (card_class, card_type, card_subtype, card_keywords[-1])
  
  return type.title()


class FABFetcherBot:
  def __init__(self):
    self.last_posted = 0
    self.comment = {}
    self.response = ''
    
    # database exists
    if(len(db) != 0):
      self.last_posted = db['last_posted']

  def setup_reddit_comment(self, comment):
    self.comment = comment
    self.find_match(comment.body)
    self.make_response(self.response, self.comment)

  def setup_debug_comment(self, text):
    self.find_match(text)
    print(self.response)

  def get_response_cards(self, cards):
    response = ''
   
    for card in cards:
      raw_name, *raw_pitch = card.split('|')
      raw_pitch = raw_pitch[0] if raw_pitch else 'all'
      pitch = clean_pitch(raw_pitch)
      name = clean_name(raw_name)
      # Request card from fabdb API
      req_kw = 'keywords=%s' % (name)
      req_pitch = '&pitch=%s' % (pitch) if pitch != 'all' else ''
      try:
        r = requests.get('https://api.fabdb.net/cards?%s%s' % (req_kw, req_pitch), timeout=10)
      except Exception as e:
        print(e)
        continue
      else:
        req_json = r.json()
        filtered = filter(lambda n: n.get('name', '').lower() == raw_name.lower(), req_json['data'])
        data = list(filtered)
        total = len(data)
        if total > 0:
          if response != '':
            response += '\n\n'
          for i, card in enumerate(data):
            print_name = get_print_name(card.get('name'), card.get('identifier'))
            print_image = card['printings'][0]['image']
            print_link = 'https://fabdb.net/cards/%s' % (card['identifier'])
            response += '[%s](%s) - [(DB)](%s)  \n' % (print_name, print_image, print_link)        
        else:
          print('No cards found')

    return response
  
  def get_response_decks(self, decks):
    response = ''
    # only iterpret the first one, for space reasons
    slug = decks[0]
    
    # Request card from fabdb API
    try:
      r = requests.get('https://api.fabdb.net/decks/%s' % (slug), timeout=10)
    except Exception as e:
      print(e)
    else:
      req_json = r.json()
      req_cards = req_json['cards']
      card_order = ['hero', 'weapon', 'equipment', 'action', 'instant', 'attack', 'defense', 'mentor', 'resource', 'other']
      data=sorted(req_cards, key=lambda x: card_order.index(x.get('type', 'other')))
      # Table Header
      response += 'Count | Card | Type\n'
      response += '---|---|----\n'
      for i, card in enumerate(data):
        print_name = get_print_name(card.get('name'), card.get('identifier'))
        print_image = card['printings'][0]['image']
        print_quantity = card['total']
        print_type = get_print_card_type(card.get('talent'), card.get('class'), card.get('type'), card.get('subType'), card.get('keywords'))
        response += '%s | [%s](%s) | %s\n' % (print_quantity, print_name, print_image, print_type)
        
    return response
  
  def find_match(self, text):
    cards = re.findall(r"\[\[(.*?)\]\]", text)
    decks = re.findall(r"\{\{(.*?)\}\}", text)
    response = ''
    if len(cards) > 0:
      response += self.get_response_cards(cards)
    if len(decks) > 0:
      ## Add line break if we've already put cards in this response
      if response != '':
          response += '___\n'
      if len(decks) > 1:
        response += '^Multiple&nbsp;deck&nbsp;codes&nbsp;found,&nbsp;only&nbsp;the&nbsp;first&nbsp;deck&nbsp;code&nbsp;will&nbsp;be&nbsp;interpreted.\n\n'
      response += self.get_response_decks(decks)
    
    response += '___\n^^^Hint:&nbsp;[[card]],&nbsp;[[card|pitch]]&nbsp;{{fabdb&nbsp;deck&nbsp;code}}.&nbsp;PM&nbsp;[me](https://www.reddit.com/message/FABFetcher)&nbsp;for&nbsp;feedback/issues!&nbsp;Card&nbsp;and&nbsp;deck&nbsp;information&nbsp;provided&nbsp;by&nbsp;[FAB&nbsp;DB](https://fabdb.net).'
    self.response = response

  def make_response(self, response, comment):
    try:
      comment.reply(response)
    except Exception as e:
      print(e)

# Setup here
# keep_alive()
bot = FABFetcherBot()
subreddit = reddit.subreddit('FABFetcherBot')
if DEBUG:
  test_comment = '[[Snatch]] and [[Command and Conquer]], with deck slugs {{invalid}}'
  bot.setup_debug_comment(test_comment)
else:
  for comment in subreddit.stream.comments(skip_existing=True):
    bot.setup_reddit_comment(comment)