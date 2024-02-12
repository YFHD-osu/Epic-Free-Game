from datetime import timedelta, datetime
from firebase_admin import credentials, firestore
import firebase_admin, os, sqlite3, urllib3, json, logging

HTTP = urllib3.PoolManager()

class Game():
  def __init__(self, title, lore, startTs, endTs, imageUrl, storeUrl) -> None:
    self.title: str = title
    self.lore: str = lore
    self.startTs: 'datetime' = startTs
    self.endTs: 'datetime' = endTs
    self.imageUrl: str = imageUrl
    self.storeUrl: str = storeUrl 
    pass

  def toDict(self) -> dict:
    return {
      "title": self.title,
      "description": self.lore,
      "startTs": self.startTs,
      "endTs": self.endTs,
      "imageUrl": self.imageUrl,
      "storeUrl": self.storeUrl
    }
  
  @staticmethod
  def fromDict(res: dict):
    return Game(
      title=res["title"],
      lore=res["lore"],
      startTs=res["startTs"],
      endTs=res["endTs"],
      imageUrl=res["imageUrl"],
      storeUrl=res["storeUrl"]
    )

  @staticmethod
  def fromJson(data: dict):
    if data["promotions"] is None or len(data["promotions"]["promotionalOffers"]) == 0:
      return
    
    return Game(
      title=data["title"],
      lore=data["description"],
      startTs=datetime.strptime(data["promotions"]["promotionalOffers"][0]["promotionalOffers"][0]["startDate"],'%Y-%m-%dT%H:%M:%S.000Z') + timedelta(hours=8),
      endTs=datetime.strptime(data["promotions"]["promotionalOffers"][0]["promotionalOffers"][0]["endDate"],'%Y-%m-%dT%H:%M:%S.000Z') + timedelta(hours=8),
      imageUrl=data["keyImages"][0]["url"],
      storeUrl=f"https://store.epicgames.com/zh-CN/p/{data['catalogNs']['mappings'][0]['pageSlug']}"
    )
  
  def toEmbed(self):
    if Settings.imageUrl == 1:
      image_payload = {'thumbnail': {'url': self.imageUrl}}
    elif Settings.imageUrl == 2:
      image_payload = {'image': {'url': self.imageUrl}}
    else:
      image_payload = {}

    return {
      "embeds": [
        {
          'title': Settings.title.replace(r"%title%", self.title),
          'description': Settings.lore.replace(r"%description%", self.lore),
          'color': int(Settings.color, 16),
          'footer': {'text': Settings.footer},
          'url': self.storeUrl,
          'timestamp': f"{self.endTs}",
          'author': {
            'name': Settings.name,
            'icon_url': Settings.iconUrl
          }
        } | (image_payload)
      ]
    }
  
  def postDiscord(self):
    resp = HTTP.request(
      "POST", 
      Settings.webhookUrl, 
      body=json.dumps(self.toEmbed()), 
      headers={'content-type': 'application/json'}
    )
    if resp.status in [200, 204]:
      logging.info(f"Success posting embed to discord wit code {resp.status}")
    else:
      logging.error(f"Error posting embed to discord with code {resp.status}")

  @staticmethod
  def fetchFree() -> list:
    response = HTTP.request("GET", Settings.apiUrl)
    games = json.loads(response.data)["data"]["Catalog"]["searchStore"]["elements"]
    free = list(filter(lambda e: e!= None, [Game.fromJson(e) for e in games]))
    logging.info(f"Detect {len(free)} free games in Epic Games")
    return free

class Settings():
  apiUrl = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions?locale=en-US&country=TW&allowCountries=TW"
  webhookUrl = "" # Discord 伺服器 Webhook 連結
  title = r"%title%" # 自訂遊戲名稱欄位 (%title% 將被替換為遊戲名稱)
  lore = r"%description%" # 自訂遊戲簡介欄位 (%description% 將被替換為遊戲簡介)
  color = "0x03b2f8" # 自訂顏色 (以16進制顏色碼表示)
  imageUrl = 2 # 圖片模式 (0=不顯示, 1=縮圖, 2=大圖)
  footer = "優惠結束時間" # 自定頁尾訊息
  name = "Epic Games 限時免費遊戲" # 自訂標題文字
  iconUrl = "https://images-ext-2.discordapp.net/external/uZwBtsyBlOPcwYXyVWYOdAI_6KvCwkBtOt_yTYbgWEQ/https/static-00.iconduck.com/assets.00/epic-games-icon-512x512-7qpmojcd.png"

  def loadDict(res: dict):
    res = {} if res == None else res
    Settings.apiUrl = res.get("API_URL", Settings.apiUrl)
    Settings.webhookUrl = res.get("WEBHOOK_URL", Settings.webhookUrl)
    Settings.title = res.get("TITLE", Settings.title)
    Settings.lore = res.get("LORE", Settings.lore)
    Settings.color = res.get("COLOR", Settings.color)
    Settings.footer = res.get("FOOTER", Settings.footer)
    Settings.name = res.get("NAME", Settings.name)
    Settings.iconUrl = res.get("ICON_URL", Settings.iconUrl)
    Settings.imageUrl = int(res.get("IMAGE_URL", str(Settings.imageUrl)))
    
    return Settings
  
  def toDict(self) -> dict:
    return {
      "API_URL": self.apiUrl,
      "WEBHOOK_URL": self.webhookUrl,
      "TITLE": self.title,
      "DESCRIPTION": self.lore,
      "COLOR": self.color,
      "IMAGE": str(self.imageUrl),
      "FOOTER": self.footer,
      "NAME" : self.name,
      "ICON_URL": self.iconUrl
    }

class DataBase(): 
  con = sqlite3.connect("database.db")
  cur = con.cursor()

  def __new__(self) -> None:
    DataBase.ensureTable("FreeGames", "title TEXT, description TEXT, effective_date INTEGER, end_date INTEGER, image TEXT, url TEXT")
    DataBase.ensureTable("Settings", "key TEXT, value TEXT")

  def ensureTable(name: str, cmds: str):
    if not len(DataBase.cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}';").fetchall()):
      DataBase.cur.execute(f"CREATE TABLE {name}({cmds});")
      DataBase.con.commit()

  def readSettings() -> Settings:
    logging.info(f"Local settings loaded")
    settingsTuple = DataBase.cur.execute(f"SELECT * FROM Settings;").fetchall()
    dataMap = dict((x, y) for x, y in settingsTuple)
    return Settings.loadDict(dataMap)
  
  def writeSettings(self, data: Settings) -> None:
    for key, value in data.toDict():
      self.cur.execute(f"""insert or replace into Settings (key, value) values
      ((select key from Settings where key = "{key}"), "{value}");""")

  def hasData(title: str) -> bool:
    return len(DataBase.cur.execute(f"SELECT * FROM FreeGames WHERE title = '{title}';").fetchall()) > 0
  
  def addData(game: Game) -> None:
    DataBase.cur.execute(f"""INSERT INTO FreeGames VALUES (
      "{game.title}", 
      "{game.lore}", 
      "{int(game.startTs.timestamp())}", 
      "{int(game.endTs.timestamp())}", 
      "{game.imageUrl}", 
      "{game.storeUrl}");
    """)
    DataBase.con.commit()

class FireStore():
  cUser: str
  cData: list = []
  client: firestore.firestore.Client

  def init():
    credList = list(filter(lambda e: e!= None, [FireStore.credLocal(), FireStore.credGit()]))
    if len(credList) == 0: raise Exception("No available credential found !")
    firebase_admin.initialize_app(credList[0])
    FireStore.client = firestore.client()
  
  def credLocal() -> credentials.Certificate:
    try: 
      file = json.load(open('credentials.json'))
      return credentials.Certificate(file["firebaseCred"])
    except: return None
  
  def credGit() -> credentials.Certificate:
    try:
      cred = json.loads(os.environ["firebaseCred"])
      return credentials.Certificate(cred)
    except: return None
  
  def users() -> list[str]:
    return [coll.id for coll in FireStore.client.collections()]
  
  def setUser(username: str):
    FireStore.cUser = username
    games = FireStore.cData = FireStore.client.collection(username).document("games").collections()
    FireStore.cData = [i.id for i in games]
    logging.info(f"Firestore user settings loaded")
    settings = FireStore.client.collection(username).document("settings").get().to_dict()
    Settings.loadDict(settings)

  def hasData(title: str) -> bool:
    if FireStore.cData is None: return False
    return title in FireStore.cData
  
  def addData(data: Game) -> None:
    dataMap = data.toDict()
    collection = FireStore.client.collection(FireStore.cUser)
    doc = collection.document("games").collection(dataMap["title"])
    doc: firestore.firestore.CollectionReference
    doc.add(dataMap)