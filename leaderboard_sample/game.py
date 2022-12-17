import dataclasses
import sqlite3
from quart import Quart,g,request,abort
import databases
from quart_schema import QuartSchema
import uuid
import random
import sqlalchemy
from rq import Queue
from redis import Redis
import string
from score_reporter import report_score

app = Quart(__name__)
QuartSchema(app)

redis_conn = Redis()
q = Queue(connection=redis_conn)

#DB Connection
async def _get_db():
    db = getattr(g, "_database", None)
    if db is None:        
        db = g.db_name = databases.Database('sqlite+aiosqlite:///var/game.db')
        await db.connect()
    return db

#DB Disconnect 
@app.teardown_appcontext
async def close_connection(exception):
    db = getattr(g, "_sqlite_db", None)
    if db is not None:
         await db.disconnect()

@dataclasses.dataclass
class Guess:
    game_id: int
    guess: str


@app.route("/games/register_callback", methods=["POST"])
async def add_callback():
    try:
        url_json = await request.get_json()
        url = url_json['url']
    except KeyError:
        return {'msg', 'url not provided'}, 400

    db = await _get_db()

    # check if the url is in the db already
    try:
        print(url)
        await db.execute(
            "INSERT INTO callback_url(url) VALUES(:url)",values={"url": url},)
    except sqlite3.IntegrityError as e:
        # Should be failing unique that's fine if not then lol
        pass

    return "success", 200


@app.route("/games/guess", methods=["POST"])
async def guess():
    db = await _get_db()
    data = {
            "uname": ''.join([random.choice(string.ascii_lowercase) for i in range(5)]),
            "guesses": random.randint(1,6),
            "win": random.choice([True, False])
            }
    print(data)


    urls = await db.fetch_all("SELECT url FROM callback_url")

    print(urls[0][0])
    for url in urls:
        q.enqueue(report_score, url[0], data)

    return "success", 200

