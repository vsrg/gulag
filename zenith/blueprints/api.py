# -*- coding: utf-8 -*-

__all__ = ()

import bleach
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
            'SELECT s.id, s.pp, s.userid, m.set_id, u.name '
            'FROM scores s '
            'LEFT JOIN users u ON s.userid = u.id '
            'LEFT JOIN maps m ON s.map_md5 = m.md5 '
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
            {"q": q + "%"}
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

    # Sanitize data from html tags
    d['data'] = bleach.clean(d['data'], tags=['p', 'br', 'b', 'i', 'u', 's', 'a', 'img', 'center'], strip=True)

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
    # Sanitize data from html tags
    d['data'] = bleach.clean(d['data'], tags=['p', 'br', 'b', 'i', 'u', 's', 'a', 'img', 'center'], strip=True)

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

    # Sanitize data from html tags
    d['data'] = bleach.clean(d['data'], tags=['p', 'br', 'b', 'i', 'u', 's', 'a', 'img', 'center'], strip=True)

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

    # Sanitize data from html tags
    d['data'] = bleach.clean(d['data'], tags=['p', 'br', 'b', 'i', 'u', 's', 'a', 'img', 'center'], strip=True)

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

    # Sanitize data from html tags
    d['data'] = bleach.clean(d['data'], tags=['p', 'br', 'b', 'i', 'u', 's', 'a', 'img', 'center'], strip=True)
    await app.state.services.database.execute(
        "UPDATE users SET userpage_content=:data WHERE id=:uid",
        {"data": d['data'], "uid": session['user_data']['id']}
    )
    return {"success": True}

@api.route('/bmap_search', methods=['POST'])
async def bmap_search():
    # Get data from request body
    d = await request.get_data()
    if d:
        d = json.loads(d.decode('utf-8'))
    else:
        return {'success': False, 'msg': 'No data received.'}

    # Create arg list for query
    arg_list = []
    args_to_query = {}

    # Checks for mode
    if 'mode' in d:
        if d['mode'] not in (None, 'null'):
            arg_list.append("`mode`=':mode'")
            args_to_query['mode'] = d['mode']

    # Checks for status
    if 'status' in d:
        status = d['status']
        if status in (None, 'null'):
            pass
        elif status == '0':
            arg_list.append('(status=2 OR status=3)')
        elif status == '1':
            arg_list.append('status=5')
        elif status == '2':
            arg_list.append('status=4')
        elif status == '3':
            arg_list.append('(status=0 OR status=1')
    # Checks for search
    if 'query' in d:
        query = d['query']
        if query not in (None, 'null'):
            arg_list.append('(artist LIKE :query OR creator LIKE :query OR version LIKE :query OR title LIKE :query)')
            args_to_query['query'] = '%' + query.replace(" ", "%") + '%'

    # Checks for frozen
    if 'frozen' in d:
        if d['frozen'] not in (None, 'null'):
            arg_list.append('frozen=1')

    # Checks for offset
    if 'offset' in d:
        if d['offset'] in (None, 'null'):
            args_to_query['offset'] = 0
        else:
            args_to_query['offset'] = d['offset']
    else:
        args_to_query['offset'] = 0

    # Convert arg_list to string, add 'AND' between every element
    arg_list = ' AND '.join(arg_list)
    if arg_list != '':
        arg_list = 'WHERE ' + arg_list

    # Fetch maps from database, don't allow duplicates
    res = await app.state.services.database.fetch_all(
        "SELECT DISTINCT(set_id), artist, creator, title, status "
        f"FROM maps {arg_list} "
        "ORDER BY last_update DESC LIMIT 30 OFFSET :offset",
        args_to_query)

    # Convert elements of res to dicts
    res = [dict(row) for row in res]

    # Loop through all maps in results
    # Shitcoding at its finest
    for el in res:
        diffs = await app.state.services.database.fetch_all(
            "SELECT mode, diff FROM maps WHERE set_id=:set_id ORDER BY diff ASC LIMIT 14",
            {"set_id": el['set_id']})
        # Convert elements of diffs to dicts
        diffs = [dict(row) for row in diffs]

        # Get diff color with spectra
        for diff in diffs:
            diff['diff_color'] = getDiffColor(diff['diff'])

        # Fetch fav count
        el['fav_count'] = await app.state.services.database.fetch_val(
            "SELECT COUNT(userid) FROM favourites WHERE setid=:set_id",
            {"set_id": el['set_id']})
        el['diffs'] = diffs

    return {"success": True, 'result': res}


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
            return{"success": False, 'msg': "Not enough data, graph is available after 3 days from getting at least 1 pp"}

        # Convert result into dicts inside array and and convert dt obj to timeago
        now = datetime.datetime.utcnow()
        for i in range(len(data)):
            data[i] = dict(data[i])
            data[i]['date'] = timeago.format(data[i]['date'], now)

        #Reverse array
        data = data[::-1]

    return {"success": True, 'data': data}

# Topg Postback
@api.route('/postback.php')
async def topg_postback(methods=['GET', 'POST']):
    if request.headers['cf-connecting-ip'] != "192.99.101.31": # Topg IP
        log(f'VOTING POSTBACK: Access denied for {request.headers["cf-connecting-ip"]}')
        return {"success": False, "msg": "Only TOPG server listing is allowed to use this route."}

    p_name = request.args.get('p_resp', default=None, type=str)
    p_ip = request.args.get('ip', default=None, type=str)

    p_id = await  app.state.services.database.fetch_val(
        "SELECT id FROM users WHERE name=:name",
        {"name": p_name} )
    if not p_id:
        log(f"VOTING POSTBACK: Vote from {p_ip}, user does not exist in database")
        return {"success": False, "msg": "User not found"}
    else:
        await app.state.services.database.execute(
            "INSERT INTO votes (userid, ip) VALUES (:id, :ip)",
            {"ip": p_ip, "id": p_id}
        )
        log(f"VOTING POSTBACK: Vote from {p_name} with IP {p_ip}")
        return {"success": True}

@api.route('/mapset_diffs', methods=['GET'])
async def mapset_diffs():
    """Get mapset diffs data by id of mapset"""
    # Get api arg
    set_id = request.args.get('id', default=None, type=int)
    if not set_id:
        return {"success": False, "msg": "You must specify 'id' arg."}

    # Fetch all maps from set by set_id
    res = await app.state.services.database.fetch_all(
        "SELECT id, version diffname, total_length, max_combo, plays, mode, bpm, "
        "cs, ar, od, hp, diff, plays, total_length length, last_update, status "
        "FROM maps WHERE set_id=:set_id ORDER BY diff ASC",
        {"set_id": set_id}
    )
    if not res:
        return {"success": False, "msg": "Mapset not found"}
    # Convert elements of res to dicts
    res = [dict(row) for row in res]

    # Loop through all maps in results
    for el in res:
        el['diff_color'] = getDiffColor(el['diff'])

    # Return data
    return {'success': True, 'result': res}
