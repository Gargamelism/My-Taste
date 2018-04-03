# this should retrieve all the movie titles and scores you've scored on taste.io

from argparse import ArgumentParser
import brotli
from csv import DictWriter
from json import loads, dumps
from requests import get, post, codes
from sys import argv
from string import join
from os import path
from jsonschema import validate, ValidationError

def email_user(email):
  return email[:email.find('@')]

def safe_read(file_path, mode):
  try:
    with open(file_path, mode) as file:
      return file.read()
  except:
    return False

def safe_write(file_path, mode, content):
  try:
    with open(file_path, mode) as file:
      file.write(content)
      return True
  except:
    return False

class TasteException(Exception):
  def __init__(self, error_message):
    Exception.__init__(self, error_message)

class TasteRatings():
  conf_schema = {
    "type": "object",
    "properties": {
      "email": {"type": "string",
                "pattern": "(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"},
      "password": {"type": "string"},
      "json": {"type": "boolean"},
      "csv": {"type": "boolean"}
    },
    "required": ["email", "password"]
  }

  base_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
                   'Accept': 'application/json, text/plain, */*',
                   'Accept-Encoding': 'gzip, deflate, br',
                   'Accept-Language': 'en-US,en;q=0.9,he;q=0.8',
                   'Cache-Control': 'no-cache',
                   'Connection': 'keep-alive',
                   'Host': 'www.taste.io',
                   'Pragma': 'no-cache'}

  kept_keys = ['year', 'name', 'user_rating', 'taste_rating', 'description']

  def __init__(self, conf):
    self._email = conf['email']
    self._pwd = conf['password']
    self._headers = TasteRatings.base_headers

    if(not self._email or not self._pwd):
      raise TasteException("missing args to initialize class")

  def build_cookie(self, response):
    cfduid = ''
    token = ''
    sid = ''

    for key in response.headers['Set-Cookie'].split(';'):
      search_res = key.find('__cfduid')
      if(search_res != -1):
        cfduid = key[search_res:]

      search_res = key.find('connect.sid')
      if(search_res != -1):
        sid = key[search_res:]

    self._token = response.json()['token']
    token = 'token=' + self._token

    sg_user_id = "sg_user_id=null"
    ajs_group_id = "ajs_group_id=null"
    ajs_anonymous_id = 'ajs_anonymous_id=%22ab91b9bf-a89e-4aa2-8ab2-bebaf5790d23%22'
    ga = "_ga=GA1.2.705052639.1521047187"

    cookie = join([cfduid, token, sid,
      sg_user_id, ajs_group_id, ajs_anonymous_id, ga], "; ")

    return cookie

  def login(self):
    payload = { 'email': self._email, 'password': self._pwd }
    response = post('https://www.taste.io/auth/local', data = payload)
    if(response.status_code != codes.ok):
      print("ERROR! server returned: <{}>".format(response.status_code))
      return False

    self._headers['Cookie'] = self.build_cookie(response)
    return True

  def is_valid_respons(self, response):
    ret = False

    if(response.status_code != codes.ok):
      print("ERROR! requst failure with <{}>".format(response.status_code))
      return ret

    if "application/json" not in response.headers['Content-Type']:
      print("ERROR! expecting json! not <{}>".format(response.headers['Content-Type']))
      return ret

    ret = True
    return ret

  def decompress_response(self, response):
    raw_content = ''
    for chunk in response.iter_content(chunk_size=128):
        raw_content += chunk

    return brotli.decompress(raw_content)

  def parse_movie(self, movie):
    movie['taste_rating'] = movie.get('stats').get('starRating')
    movie['user_rating'] = movie.get('highlightRating')

    movie.pop('stats')
    movie.pop('highlightRating')
    return { kept_key: unicode(movie[kept_key]).encode('utf-8') for kept_key in TasteRatings.kept_keys }

  def ratings(self):
    base_url = "https://www.taste.io/api/users/{}/ratings".format(
        email_user(self._email))

    movies = []
    movies_left = True
    offset = 0
    while movies_left:
      response = get(base_url + "?offset={}".format(offset), headers=self._headers)

      if(not self.is_valid_respons(response)):
        return 1

      json_response = loads(self.decompress_response(response))

      length = len(json_response['movies'])
      if(length == 0):
        movies_left = False

      movies += json_response['movies']
      offset += length

    parsed_movies = []
    for movie in movies:
      parsed_movies.append(self.parse_movie(movie))

    return parsed_movies

def parse_args():
  parser = ArgumentParser(description = 'Retrieve your taste.io ratings as a json/csv')

  parser.add_argument('-C', '--conf-file', required=False, dest='conf_file', default='my_taste_conf.json', help='configuration file with a JSON with the keys \'email\' and \'password\' if not provided, it will create one automatically')

  parser.add_argument('-e', '--email', required=False, dest='email', help='email used to login to taste.io')
  parser.add_argument('-p', '--password', required=False, dest='password', help='password used to login to taste.io')

  parser.add_argument('-j', '--json', action='store_const', required=False, dest='json',
                      const=True, help='output is in json form')

  parser.add_argument('-c', '--csv', action='store_const', required=False, dest='csv',
                      const=True, help='output is in csv form')

  parsed = parser.parse_args(argv[1:])
  return [parsed.conf_file, parsed.email, parsed.password, parsed.json, parsed.csv]

def print_json_file(file_name, json):
  out_file = open("{}.json".format(file_name), "w")
  out_file.write(dumps(json, indent=4, sort_keys=True))
  out_file.close()

def print_csv_file(file_name, parsed_movies):
  with open("{}.csv".format(file_name), 'w') as csvfile:
    writer = DictWriter(csvfile, fieldnames=TasteRatings.kept_keys)

    writer.writeheader()
    for movie in parsed_movies:
      writer.writerow(movie)

def parse_conf_file(conf_file, email, pwd, json, csv):
  conf = {}
  if(not path.exists(conf_file) or (not path.getsize(conf_file) > 0)):
    conf['email'] = email
    conf['password'] = pwd

    if(json == None):
      json = False
    conf['json'] = json

    if(csv == None):
      csv = False
    conf['csv'] = csv

    safe_write(conf_file, 'w', dumps(conf))
  else:
    conf = loads(safe_read(conf_file, 'r'))

  try:
    validate(conf, TasteRatings.conf_schema)
  except ValidationError as e:
    print(str(e))
    return False

  return conf

def main():
    conf_file, email, pwd, json, csv = parse_args()

    conf = parse_conf_file(conf_file, email, pwd, json, csv)
    if(not conf):
      print("Not done!")
      return 1

    taste_ratings = TasteRatings(conf)
    if(not taste_ratings.login()):
      print("Not done!")
      return 1

    parsed_movies = taste_ratings.ratings()

    file_name = email_user(conf['email']) + "_taste_ratings"

    if(json or conf['json'] or (not json and not csv)):
      print_json_file(file_name, parsed_movies)

    if(csv or conf['csv']):
      print_csv_file(file_name, parsed_movies)

    print("Done!")

if __name__ == "__main__":
    main()
