import praw
import os
import re
import requests
from replit import db
from keep_alive import keep_alive

DEBUG = False
BOT_NAME = 'fabfetcher'

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

def get_hint_text(text):
  return text.replace(' ', '&nbsp;')


class FABFetcherBot:
  def __init__(self):
    self.last_posted = 0
    self.comment = {}
    self.response = ''
    
    # database exists
    if(len(db) != 0):
      self.last_posted = db['last_posted']

  def setup_reddit_comment(self, comment):
    if(str(comment.author).lower() != BOT_NAME):
      print('comment found')
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
        r.raise_for_status()
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
          for card in enumerate(data):
            print_name = get_print_name(card.get('name'), card.get('identifier'))
            print_image = card['printings'][0]['image']
            print_link = 'https://fabdb.net/cards/%s' % (card['identifier'])
            response += '[%s](%s) - [(DB)](%s)  \n' % (print_name, print_image, print_link)        
        else:
          print('No cards found')

    return response
  
  def get_response_decks(self, decks):
    response = ''
    
    for slug in decks:
      # Request deck from fabdb API
      try:
        r = requests.get('https://api.fabdb.net/decks/%s' % (slug), timeout=10)
        r.raise_for_status()
      except Exception as e:
        print(e)
      else:
        req_json = r.json()
        req_cards = req_json.get('cards', [])
        # check for sideboard
        req_side = req_json.get('sideboard', [])
        has_side = len(req_side) > 0
        card_order = ['hero', 'weapon', 'equipment', 'action', 'instant', 'attack', 'defense', 'mentor', 'resource', 'other']
        data=sorted(req_cards, key=lambda x: card_order.index(x.get('type', 'other')))
        # Table Header
        response += '[%s](https://fabdb.net/decks/%s) - Format: %s\n\n' % (req_json.get('name'), slug, req_json.get('format').title())
        # Setup header depending on if there is a sideboard or not
        if has_side:
          response += 'Side | Main | Card | Type\n'
          response += ':---:|:---:|---|----\n'
        else:
          response += 'Main | Card | Type\n'
          response += ':---:|---|----\n'

        # Card count vars
        main_count = 0
        side_count = 0
        
        # Card enumeration
        for i, card in enumerate(data):
          print_name = get_print_name(card.get('name'), card.get('identifier'))
          print_image = card['printings'][0]['image']
          # Don't include Hero cards in the mainboard count
          mainboard = card.get('total') - card.get('totalSideboard') if card.get('type') != 'hero' else 0
          sideboard = card.get('totalSideboard')
          main_count += mainboard
          side_count += sideboard
          print_mainboard = mainboard if mainboard > 0 else '&nbsp;'
          print_sideboard = sideboard if sideboard > 0 else '&nbsp;'
          print_type = get_print_card_type(card.get('talent'), card.get('class'), card.get('type'), card.get('subType'), card.get('keywords'))
          
          if has_side:
            response += '%s | %s | [%s](%s) | %s\n' % (print_sideboard, print_mainboard, print_name, print_image, print_type)
          else:
            response += '%s | [%s](%s) | %s\n' % (print_mainboard, print_name, print_image, print_type)

        # Add final card counts at the bottom
        if has_side:
          response += '**%s** | **%s** |  | \n' % (side_count, main_count)
        else:
          response += '**%s** | | \n' % (main_count)
        return response
        
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
        response += get_hint_text('^Multiple deck codes found, only the first valid deck code will be interpreted.\n\n')
      response += self.get_response_decks(decks)
    
    if response != '':
      response += get_hint_text('___\n^^^Hint: [[card]], [[card|pitch]] {{fabdb deck code}}. PM [me](https://www.reddit.com/message/FABFetcher) for feedback/issues! Card and deck information provided by [FAB DB](https://fabdb.net).')
      self.response = response

  def make_response(self, response, comment):
    try:
      if response != '':
        print('responding')
        comment.reply(response)
    except Exception as e:
      print(e)

# Setup here
bot = FABFetcherBot()
print('FAB Fetcher Bot is now running')
if DEBUG:
  test_comment = '{{gBVQWAdJ}} has a sideboard'
  # test_comment = '{{EPGBqxWl}} has no sideboard'
  # test_comment = '{{EGdlZLQA}} blitz'
  bot.setup_debug_comment(test_comment)
else:
  keep_alive()
  subreddit = reddit.subreddit('FABFetcherBotTest')
  for comment in subreddit.stream.comments(skip_existing=True):
    bot.setup_reddit_comment(comment)