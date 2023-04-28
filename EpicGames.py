from datetime import datetime, timedelta
import sqlite3, requests, json, logging

logging.basicConfig(
  level = logging.INFO,
  format = '[%(asctime)s] [%(levelname)s] %(message)s',
  datefmt = '%Y/%m/%d %I:%M:%S'
)

def main() -> None:
  try:
    settings = json.loads(open("config.json", 'r').read())
    API_URL = settings['API_URL']
    WEBHOOK_URL = settings['WEBHOOK_URL']
  except json.decoder.JSONDecodeError:
    logging.error('config.json file has one or more syntax error.')
    return
  except KeyError as error:
    logging.error(f'config.json is missing value(s) that required. ({error})')
    return

  logging.info('Settings loaded sucessfuly.')
  
  try:
    response = requests.get(API_URL)
    free_game = json.loads(response.text)["data"]["Catalog"]["searchStore"]["elements"]
  except:
    logging.info('')
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
    image = data["keyImages"][-1]["url"]
    url = f"https://store.epicgames.com/zh-CN/p/{data['catalogNs']['mappings'][0]['pageSlug']}"
    cur.execute(f'INSERT INTO FreeGames VALUES ("{title}", "{description}", "{int(effective_date.timestamp())}", "{int(end_date.timestamp())}", "{image}", "{url}");')
    
    message = {
      'embeds': [
        {
          'title': title,
          'description': description,
          'color': 0x03b2f8,
          'image': {'url': image},
          'footer': {'text': f'優惠結束時間'},
          'url': url,
          'timestamp': f"{end_date}",
          'author': {
            'name': 'Epic Games 限時免費遊戲',
            'icon_url': 'https://images-ext-2.discordapp.net/external/uZwBtsyBlOPcwYXyVWYOdAI_6KvCwkBtOt_yTYbgWEQ/https/static-00.iconduck.com/assets.00/epic-games-icon-512x512-7qpmojcd.png'
          }
        }
      ]
    }
    response = requests.post(WEBHOOK_URL, data=json.dumps(message), headers={'content-type': 'application/json'})

  con.commit()

if __name__ == "__main__":
  main()