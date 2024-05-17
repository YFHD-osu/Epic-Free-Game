import logging, argparse
from database import DataBase, Game, FireStore

logging.basicConfig(
  level = logging.INFO,
  format = '[%(asctime)s] [%(levelname)s] %(message)s',
  datefmt = '%Y/%m/%d %I:%M:%S'
)

def firebase() -> None:
  FireStore.init()
  games: list[Game] = Game.fetchFree()
  for user in FireStore.users():
    FireStore.setUser(user)
    for data in games:
      if FireStore.hasData(data.title):
        logging.info(f"Skipping {data.title}, Embed already posted in discord")
        continue
      data.postDiscord()
      FireStore.addData(data)

def local() -> None:
  DataBase.init()
  DataBase.readSettings()
  games: list[Game] = Game.fetchFree()
  for data in games:
    if DataBase.hasData(data.title): 
      logging.info(f"Skipping {data.title}, Embed already posted in discord")
      continue
    data.postDiscord()
    DataBase.addData(data)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--mode", type=str, default="local")

  args = parser.parse_args()
  if (args.mode == "local"):
    logging.info("Starting server with local database")
    local()
  elif (args.mode == "firestore"):
    logging.info("Starting server with firestore")
    firebase()