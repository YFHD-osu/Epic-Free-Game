from datetime import datetime, timedelta
import sqlite3, urllib3, json, logging

http = urllib3.PoolManager()
logging.basicConfig(
  level = logging.INFO,
  format = '[%(asctime)s] [%(levelname)s] %(message)s',
  datefmt = '%Y/%m/%d %I:%M:%S'
)

def main() -> None:
  try: # Load settings from config.json
    settings = json.loads(open("config.json", 'r').read())
    API_URL = settings['API_URL']
    WEBHOOK_URL = settings['WEBHOOK_URL']
    TITLE : str = settings['TITLE']
    DESCRIPTION : str = settings['DESCRIPTION']
    COLOR : str = settings['COLOR']
    IMAGE : int = int(settings['IMAGE'])
    FOOTER : str = settings['FOOTER']
    NAME : str = settings['NAME']
    ICON_URL : str = settings['ICON_URL']
  except FileNotFoundError:
    logging.error('Cannot found file config.json')
    return
  except json.decoder.JSONDecodeError:
    logging.error('config.json file has one or more syntax error.')
    return
  except KeyError as error:
    logging.error(f'config.json is missing value(s) that required. ({error})')
    return
  logging.info('Settings loaded sucessfuly.')
  
  try:
    response = http.request("GET", API_URL)
    free_game = json.loads(response.data)["data"]["Catalog"]["searchStore"]["elements"]
  except:
    logging.error('Cannot connect to Epic Games API')
    return

  con = sqlite3.connect("database.db")
  cur = con.cursor()
  
  if not len(cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='FreeGames';").fetchall()):
    cur.execute("CREATE TABLE FreeGames(title TEXT, description TEXT, effective_date INTEGER, end_date INTEGER, image TEXT, url TEXT);")

  for data in free_game:
    if data["promotions"] is None or len(data["promotions"]["promotionalOffers"]) == 0: continue
    if len(cur.execute(f"SELECT * FROM FreeGames WHERE title = '{data['title']}';").fetchall()) != 0: continue

    title = data["title"]
    description = data["description"]
    effective_date = datetime.strptime(data["promotions"]["promotionalOffers"][0]["promotionalOffers"][0]["startDate"],'%Y-%m-%dT%H:%M:%S.000Z') + timedelta(hours=8)
    end_date = datetime.strptime(data["promotions"]["promotionalOffers"][0]["promotionalOffers"][0]["endDate"],'%Y-%m-%dT%H:%M:%S.000Z') + timedelta(hours=8)
    image = data["keyImages"][0]["url"]
    url = f"https://store.epicgames.com/zh-CN/p/{data['catalogNs']['mappings'][0]['pageSlug']}"
    
    if IMAGE == 1:
      image_payload = {'thumbnail': {'url': image}}
    elif IMAGE == 2:
      image_payload = {'image': {'url': image}}
    else:
      image_payload = {}

    payload = {
      'embeds': [
        {
          'title': TITLE.replace('%title%', title),
          'description': DESCRIPTION.replace(r"%description%", description),
          'color': int(COLOR, 16),
          'footer': {'text': FOOTER},
          'url': url,
          'timestamp': f"{end_date}",
          'author': {
            'name': NAME,
            'icon_url': ICON_URL
          }
        } | (image_payload)
      ]
    }
    
    try: 
      http.request("POST", WEBHOOK_URL, body=json.dumps(payload), headers={'content-type': 'application/json'})
    except:
      logging.error("Cannot post webhook message.")
      continue

    cur.execute(f'INSERT INTO FreeGames VALUES ("{title}", "{description}", "{int(effective_date.timestamp())}", "{int(end_date.timestamp())}", "{image}", "{url}");')

  con.commit()

if __name__ == "__main__":
  main()