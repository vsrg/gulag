# -*- coding: utf-8 -*-

__all__ = ()

from curses.ascii import isdigit
import datetime
import json
import databases
import service_identity
import timeago

import app.state.services
from app.constants.privileges import Privileges
from pandas import to_datetime

from quart import (Blueprint, redirect, render_template,
                   request, session, send_file, jsonify)

from app.objects.player import Player
from zenith.objects.constants import mode_gulag_rev, mode2str
from zenith.objects.utils import *
from zenith import zconfig

api = Blueprint('api', __name__)
MODE_CONVERT = {
    0: "osu!Standard",
    1: "osu!Taiko",
    2: "osu!Catch",
    3: "osu!Mania",
    4: "osu!Standard+RX",
    5: "osu!Taiko+RX",
    6: "osu!Catch+RX",
    8: "osu!Standard+AP",
}

@api.route('/')
async def main():
    return {'success': False, 'msg': 'Please specify route'}

@api.route('/get_records')
async def get_records():
    #TODO: Make it faster
    records = {}
    for i in range(0, 9):
        if i == 7:
            continue
        record = await app.state.services.database.fetch_one(
            f'SELECT s.id, s.pp, s.userid, m.set_id, u.name '
            f'FROM scores s '
            f'LEFT JOIN users u ON s.userid = u.id '
            f'LEFT JOIN maps m ON s.map_md5 = m.md5 '
            f'WHERE s.mode = {i} AND m.status=2 AND u.priv & 1 '
             'AND grade!="f"'
             'ORDER BY pp DESC LIMIT 1;'
        )
        record = dict(record)
        record['id'] = str(record['id'])
        record['mode_str'] = MODE_CONVERT[i]
        records[mode2str[i]] = record

    return {"success": True, "records": records}

@api.route('/get_last_registered', methods=["GET"])
async def getLastRegistered():

    res = await app.state.services.database.fetch_all(
        "SELECT id, name, country, creation_time "
        "FROM users WHERE priv & 1 "
        "ORDER BY creation_time DESC "
        "LIMIT 12",
    )
    i = 0
    res_n = {}
    for el in res:
        el = dict(el)
        el['creation_time'] = time_ago(datetime.datetime.utcnow(),
                        to_datetime(datetime.datetime.fromtimestamp(int(el['creation_time'])),
                        format="%Y-%m-%d %H:%M:%S"), time_limit=1) + "ago"
        res_n[f"el{i}"] = el
        i += 1
    del(res)

    return {"success": True, "users": res_n}

@api.route('/get_priv_badges', methods=['GET'])
async def get_priv_badges():
    id = request.args.get('id', default=None, type=int)
    if not id:
        return {"success": False, "msg": "id not specified"}
    res = await app.state.services.database.fetch_val(
        "SELECT priv FROM users WHERE id=:uid",
        {"uid": id}
    )
    uprv = Privileges(res)
    badges = []
    if id in zconfig.owners:
        badges.append(("OWNER", "text-red-500"))
    if Privileges.DEVELOPER in uprv:
        badges.append(("DEV", "text-purple-500"))
    if Privileges.ADMINISTRATOR in uprv:
        badges.append(("ADMIN", "text-yellow-500"))
    if Privileges.MODERATOR in uprv and Privileges.ADMINISTRATOR not in uprv:
        badges.append(("GMT", "text-green-500"))
    if Privileges.NOMINATOR in uprv:
        badges.append(("BN", "text-blue-500"))
    if Privileges.ALUMNI in uprv:
        badges.append(("ALUMNI", "text-red-600"))
    if Privileges.WHITELISTED in uprv:
        badges.append(("✔", "text-green-500"))
    if Privileges.SUPPORTER in uprv:
        if Privileges.PREMIUM in uprv:
            badges.append(["❤❤", "text-pink-500"])
        else:
            badges.append(["❤", "text-pink-500"])
    elif Privileges.PREMIUM in uprv:
        badges.append(["❤❤", "text-pink-500"])
    if Privileges.NORMAL not in uprv:
        badges.append(("RESTRICTED", "text-white"))
    return {"success":True, "badges": badges}

@api.route('/update_color', methods=['POST'])
async def update_color():
    if not 'authenticated' in session:
        return {'success': False, 'msg': 'Login required.'}
    else:
        await updateSession(session)

    color = request.args.get('color', default=230, type=int)
    color = int(color)

    if color > 360:
        color = 360
    if color < 0:
        color = 0

    session['color'] = color
    """
    await app.state.services.database.execute(
        "UPDATE customs SET color=:color WHERE userid=:id",
        {"color": color, "id": session['user_data']['id']}
    )
    """
    return {"success": True, "msg": f'Color changed to {color}'}

@api.route('/change_default_mode', methods=['POST'])
async def changeDefaultMode():
    if not 'authenticated' in session:
        return {'success': False, 'msg': 'Login required.'}
    else:
        await updateSession(session)

    mode = request.args.get('mode', default=0, type=int)
    if mode not in [0,1,2,3,4,5,6,8]:
        return {"success": False, "msg": "Mode must be in range of 0-8 excluding 7."}

    await app.state.services.database.execute(
        "UPDATE users SET preferred_mode=:mode WHERE id=:uid",
        {"mode": mode, "uid": session['user_data']['id']}
    )
    return {"success": True, "msg": f"Mode successfully changed to {mode}"}

""" /search_users"""
@api.route('/search_users', methods=['GET']) # GET
async def search_users():
    q = request.args.get('q', type=str)
    if not q:
        return {"success": False, "users": []}
    if q == '':
        return {"success": False, "users": []}

    if 'authenticated' in session and session['user_data']['is_staff'] == True:
        # User is GMT/ADMIN/DEV
        res = await app.state.services.database.fetch_all(
            'SELECT id, name '
            'FROM `users` '
            'WHERE `name` LIKE :q '
            'AND id!=1 '
            'LIMIT 5',
            {"q": q.join("%%")}
        )
    else:
        # Normal User
        res = await app.state.services.database.fetch_all(
            'SELECT id, name '
            'FROM `users` '
            'WHERE priv & 1 AND `name` LIKE :q '
            'AND id!=1 '
            'LIMIT 5',
            {"q": q.join("%%")}
        )

    new_res = []
    for el in res:
        new_res.append(dict(el))

    res = new_res
    del(new_res)

    return {"success": True, "users": res}

"""/update_user_discord"""
@api.route('/update_user_discord', methods=['POST'])
async def update_user_discord():
    if not 'authenticated' in session:
        return {'success': False, 'msg': 'Login required.'}
    else:
        await updateSession(session)

    d = await request.get_data()
    d = json.loads(d.decode('utf-8'))

    user = await app.state.services.database.fetch_val(
        "SELECT 1 FROM customs WHERE userid=:id",
        {"id": session['user_data']['id']}
    )
    if user:
        await app.state.services.database.execute(
            "UPDATE customs SET discord_tag=:data WHERE userid=:uid",
            {"data": d['data'], "uid": session['user_data']['id']}
        )
    else:
        await app.state.services.database.execute(
            "INSERT INTO customs (`userid`, `discord_tag`) VALUES (:uid, :data)",
            {"data": d['data'], "uid": session['user_data']['id']}
        )
    return {'success': True}

"""/update_user_location"""
@api.route('/update_user_location', methods=['POST'])
async def update_user_location():
    if not 'authenticated' in session:
        return {'success': False, 'msg': 'Login required.'}
    else:
        await updateSession(session)

    d = await request.get_data()
    d = json.loads(d.decode('utf-8'))

    user = await app.state.services.database.fetch_val(
        "SELECT 1 FROM customs WHERE userid=:id",
        {"id": session['user_data']['id']}
    )
    if user:
        await app.state.services.database.execute(
            "UPDATE customs SET location=:data WHERE userid=:uid",
            {"data": d['data'], "uid": session['user_data']['id']}
        )
    else:
        await app.state.services.database.execute(
            "INSERT INTO customs (`userid`, `location`) VALUES (:uid, :data)",
            {"data": d['data'], "uid": session['user_data']['id']}
        )
    return {'success': True}

"""/update_user_interests"""
@api.route('/update_user_interests', methods=['POST'])
async def update_user_interests():
    if not 'authenticated' in session:
        return {'success': False, 'msg': 'Login required.'}
    else:
        await updateSession(session)

    d = await request.get_data()
    d = json.loads(d.decode('utf-8'))

    user = await app.state.services.database.fetch_val(
        "SELECT 1 FROM customs WHERE userid=:id",
        {"id": session['user_data']['id']}
    )
    if user:
        await app.state.services.database.execute(
            "UPDATE customs SET interests=:data WHERE userid=:uid",
            {"data": d['data'], "uid": session['user_data']['id']}
        )
    else:
        await app.state.services.database.execute(
            "INSERT INTO customs (`userid`, `interests`) VALUES (:uid, :data)",
            {"data": d['data'], "uid": session['user_data']['id']}
        )
    return {'success': True}

"""/update_user_website"""
@api.route('/update_user_website', methods=['POST'])
async def update_user_website():
    if not 'authenticated' in session:
        return {'success': False, 'msg': 'Login required.'}
    else:
        await updateSession(session)

    d = await request.get_data()
    d = json.loads(d.decode('utf-8'))

    user = await app.state.services.database.fetch_val(
        "SELECT 1 FROM customs WHERE userid=:id",
        {"id": session['user_data']['id']}
    )
    if user:
        await app.state.services.database.execute(
            "UPDATE customs SET website=:data WHERE userid=:uid",
            {"data": d['data'], "uid": session['user_data']['id']}
        )
    else:
        await app.state.services.database.execute(
            "INSERT INTO customs (`userid`, `website`) VALUES (:uid, :data)",
            {"data": d['data'], "uid": session['user_data']['id']}
        )
    return {'success': True}

@api.route('/update_aboutme', methods=['POST'])
async def update_aboutme():
    if not 'authenticated' in session:
        return {'success': False, 'msg': 'Login required.'}
    else:
        await updateSession(session)

    d = await request.get_data()
    d = json.loads(d.decode('utf-8'))
    await app.state.services.database.execute(
        "UPDATE users SET userpage_content=:data WHERE id=:uid",
        {"data": d['data'], "uid": session['user_data']['id']}
    )
    return {"success": True}

@api.route('/bmap_search')
async def bmap_search():
    q = request.args.get('q', type=str, default=None)
    mode = request.args.get('mode', type=int, default=None)
    status = request.args.get('status', type=int, default=None)
    offset = request.args.get('o', type=int, default=0)

    # Define search query args and string for later usage
    search_q = []
    search_q_args = {}
    search_q_args['offset'] = offset

    # Check mode, append to query if present
    if mode:
        if mode < 0 or mode > 3:
            return {"success": False, "msg": "Mode must be in range 0-3"}
        search_q.append("mode=:mode")
        search_q_args['mode'] = mode

    # Check status, append to query if present
    if status:
        if status < 0 or status > 5:
            return {"success": False, "msg": "Status must be in range 0-5"}
        search_q.append("status=:status")
        search_q_args['status'] = status

    # Simple Search Engine xD. Dear god i need to figure out how to use match aginst
    if q:
        search_q.append("creator LIKE :q OR title LIKE :q OR artist LIKE :q OR version LIKE :q")
        search_q_args['q'] = q

    search_q_new = ""
    i = 1
    #Parse qury args
    for el in search_q:
        if i != len(search_q):
            search_q_new += el + ' AND '
        else:
            search_q_new += el
        i += 1

    res = await app.state.services.database.fetch_all(
        "SELECT DISTINCT(set_id), status, artist, creator, title "
        f"FROM maps WHERE {search_q_new} "
        "ORDER BY last_update DESC LIMIT 30 OFFSET :offset",
        search_q_args
    )
    print(res)
    print("\n\nSELECT DISTINCT(set_id), status, artist, creator, title ")
    print(f"FROM maps WHERE {search_q_new} ")
    print("ORDER BY last_update DESC LIMIT 30 OFFSET :offset")
    print(search_q_args, "\n\n")

    return {"success": True, "result": res}

@api.route('/get_pp_history')
async def get_pp_history():
    userid = request.args.get('u', type=int)
    mode = request.args.get('m', type=int)

    if not mode and mode not in (0,1,2,3,4,5,6,8):
        return {"success": False, "msg": "'m' argument (mode) must be in range 0-8 excluding 7."}

    if not userid:
        return {"success": False, "msg": "You must specify 'u' arg."}
    u = await app.state.services.database.fetch_val(
        "SELECT 1 FROM users WHERE id = :uid",
        {"uid": userid}
    )
    if not u:
        return {"success": False, "msg": "User not found"}
    else:
        # Get current time and substract one day to get yesterday midnight +1s
        now = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime("%Y-%m-%d 00:00:01")
        # Fetch data from db
        data = await app.state.services.database.fetch_all(
            "SELECT pp, DATE_FORMAT(date,'%Y-%m-%d') AS `date` "
            "FROM pp_graph_data "
            "WHERE mode=:m AND id=:uid AND subdate(current_date, 1) "
            "AND date < :today "
            "ORDER BY date DESC LIMIT 90",
            {"m": mode, "uid": userid, 'today': now}
        )
        #Delete unusued vars
        del(now, userid, mode)
        if len(data) < 2:
            return{"success": False, 'msg': "Not enough data, graph is aviable after 3 days from getting at least 1 pp"}

        # Convert result into dicts inside array and and convert dt obj to timeago
        now = datetime.datetime.utcnow()
        for i in range(len(data)):
            data[i] = dict(data[i])
            data[i]['date'] = timeago.format(data[i]['date'], now)

        #Reverse array
        data = data[::-1]
    return {"success": True, 'data': data}
