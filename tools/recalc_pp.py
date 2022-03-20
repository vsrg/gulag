
import asyncio
from cmyui import AsyncSQLPool
import datetime
db_cridentials = {
    "user": "admin",
    "password": "QrFT^W5tPqKW=n3b6L!Ua=RW",
    "db": "gulag",
    "host": "localhost"
}
db = AsyncSQLPool()
async def updatestatspp():
    now = datetime.datetime.now()
    await db.connect(db_cridentials)
    for mode in (0,1,2,3,4,5,6,8):
        res = await db.fetchall(
            "SELECT u.id, u.priv, u.country, s.pp "
            "FROM users u "
            "LEFT JOIN stats s ON u.id=s.id "
            "WHERE s.mode=%s AND u.id != 1 ORDER BY u.id ASC",
            [0]
        )
        print(f"\n\n\n\nMode {mode}\n{res=}\n\n\n\n")
        for el in res:
            print(f"Working on {el['id']}, mode {mode}")
            best_scores = await db.fetchall(
                "SELECT s.pp FROM scores s "
                "INNER JOIN maps m ON s.map_md5 = m.md5 "
                "WHERE s.userid = %s AND s.mode = %s "
                "AND s.status = 2 AND m.status IN (2, 3) "  # ranked, approved
                "ORDER BY s.pp DESC",
                [el['id'], mode],
            )

            top_100_pp = best_scores[:100]
            weighted_pp = sum(row["pp"] * 0.95**i for i, row in enumerate(top_100_pp))
            total_scores = len(best_scores)
            bonus_pp = 416.6667 * (1 - 0.95**total_scores)
            pp = round(weighted_pp + bonus_pp)

            await db.execute(
                "UPDATE stats SET pp=%s WHERE id=%s AND mode=%s",
                [pp, el['id'], mode]
            )
    end = datetime.datetime.now()
    print(f"Execution Time: {end - now}")
    return "Done"

asyncio.run(updatestatspp())