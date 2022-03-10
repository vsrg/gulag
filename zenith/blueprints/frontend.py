# -*- coding: utf-8 -*-

__all__ = ()

import datetime
import hashlib
import os
from re import S
import time
from markdown import markdown as md
from PIL import Image

import bcrypt
from sqlalchemy import null
from app.constants.privileges import Privileges
from app.objects.player import Player
from app.state import website as zglob
import app.state
from cmyui.logging import Ansi, log
from pathlib import Path
from quart import (Blueprint, redirect, render_template, request, send_file,
                   session)
from zenith import zconfig
from zenith.objects import regexes, utils
from zenith.objects.utils import flash, flash_tohome, validate_password
from app.constants import gamemodes

frontend = Blueprint('frontend', __name__)

@frontend.route('/')
async def home():
    if 'authenticated' in session:
        await utils.updateSession(session)

    return await render_template('home.html', methods=['GET'])

@frontend.route('/login', methods=['GET'])
async def login():
    if 'authenticated' in session:
        return await utils.flash_tohome('error', "You're already logged in!")
    return await render_template('login.html')

@frontend.route('/login', methods=['POST'])
async def login_post():
    if 'authenticated' in session:
        return await utils.flash_tohome('error', "You're already logged in!")


    form = await request.form
    username = form.get('username', type=str)
    passwd_txt = form.get('password', type=str)

    if username is None or passwd_txt is None:
        return await utils.flash_tohome('error', 'Invalid parameters.')

    # check if account exists
    user_info = await app.state.services.database.fetch_one(
        'SELECT id, name, email, priv, '
        'pw_bcrypt, silence_end '
        'FROM users '
        'WHERE safe_name = :sn',
        {"sn": utils.get_safe_name(username)}
    )
    # user doesn't exist; deny post
    if not user_info:
        return await render_template('login.html', flash={"msg":"Invalid username or password."})

    # convert to dict because databases
    user_info = dict(user_info)

    # NOTE: Bot isn't a user.
    if user_info['id'] == 1:
        return await render_template('login.html', flash={"msg":"Invalid username or password."})

    # cache and other related password information
    bcrypt_cache = zglob.cache['bcrypt']
    pw_bcrypt = user_info['pw_bcrypt'].encode()
    pw_md5 = hashlib.md5(passwd_txt.encode()).hexdigest().encode()

    # check credentials (password) against db
    # intentionally slow, will cache to speed up
    if pw_bcrypt in bcrypt_cache:
        if pw_md5 != bcrypt_cache[pw_bcrypt]: # ~0.1ms
            return await render_template('login.html', flash={"msg":"Invalid username or password."})
    else: # ~200ms
        if not bcrypt.checkpw(pw_md5, pw_bcrypt):
            return await render_template('login.html', flash={"msg":"Invalid username or password."})

        # login successful; cache password for next login
        bcrypt_cache[pw_bcrypt] = pw_md5

    # user not verified; render verify
    if not user_info['priv'] & Privileges.VERIFIED:
        return await render_template('verify.html')


    # login successful; store session data

    session['authenticated'] = True
    session['user_data'] = {}
    await utils.updateSession(session, int(user_info['id']))

    return await utils.flash_tohome('success', f"Welcome back {username}!")

@frontend.route('/logout', methods=['GET'])
async def logout():
    if 'authenticated' not in session:
        return await utils.flash_tohome('error', "You can't log out if you're not logged in.")

    # clear session data
    session.pop('authenticated', None)
    session.pop('user_data', None)

    # render login
    return await utils.flash_tohome('success', "Successfully logged out!")

@frontend.route('/register', methods=['GET'])
async def register():
    if 'authenticated' in session:
        return await utils.flash_tohome('error', "You're already logged in'!")

    return await render_template('register.html', message=None)

@frontend.route('/register', methods=['POST'])
async def register_post():
    if 'authenticated' in session:
        return await utils.flash_tohome('error', "You're already logged in.")

    if not zconfig.registration:
        return await utils.flash_tohome('error', 'Registrations are currently disabled.')

    form = await request.form
    username = form.get('username', type=str)
    email = form.get('email', type=str)
    passwd_txt = form.get('password', type=str)
    passwd_txt_repeat = form.get('password-confirm', type=str)
    if username is None or email is None or passwd_txt is None:
        return await utils.flash_tohome('error', 'Invalid parameters.')
    if passwd_txt != passwd_txt_repeat:
        return await render_template('register.html', message={"password": "Passwords didn't match"})

    if zconfig.hCaptcha_sitekey != 'changeme':
        captcha_data = form.get('h-captcha-response', type=str)
        if (
            captcha_data is None or
            not await utils.validate_captcha(captcha_data)
        ):
            return await render_template('register.html', message={"captcha": 'Captcha Failed'})

    # Usernames must:
    # - be within 2-15 characters in length
    # - not contain both ' ' and '_', one is fine
    # - not be in the config's `disallowed_names` list
    # - not already be taken by another player
    # check if username exists
    if not regexes.username.match(username):
        return await render_template('register.html', message={"name": 'Invalid Username'})

    if '_' in username and ' ' in username:
        return await render_template('register.html', message={"name": 'Username may contain "_" or " ", but not both.'})

    if username in zconfig.disallowed_names:
        return await render_template('register.html', message={"name": 'Disallowed username; pick another'})

    if await app.state.services.database.fetch_one(
        'SELECT 1 FROM users WHERE name=:name',
        {"name": username}
        ):
            return await render_template('register.html', message={"name": 'Username already taken by another user.'})
    # Emails must:
    # - match the regex `^[^@\s]{1,200}@[^@\s\.]{1,30}\.[^@\.\s]{1,24}$`
    # - not already be taken by another player
    if not regexes.email.match(email):
        return await render_template('register.html', message={"email": 'Invalid email syntax.'})

    if await app.state.services.database.fetch_one(
        'SELECT 1 FROM users WHERE email = :email',
        {"email": email}
        ):
            return await render_template('register.html', message={"email": 'Email already taken by another user.'})
    # Passwords must:
    # - be within 8-32 characters in length
    # - have more than 3 unique characters
    # - not be in the config's `disallowed_passwords` list
    if not 8 <= len(passwd_txt) <= 48:
        return await render_template('register.html', message={"password": 'Password must be 8-48 characters in length'})

    if len(set(passwd_txt)) <= 3:
        return await render_template('register.html', message={"password": 'Password must have more than 3 unique characters.'})

    if passwd_txt.lower() in zconfig.disallowed_passwords:
        return await render_template('register.html', message={"password": 'That password was deemed too simple.'})

    # TODO: add correct locking
    # (start of lock)
    pw_md5 = hashlib.md5(passwd_txt.encode()).hexdigest().encode()
    pw_bcrypt = bcrypt.hashpw(pw_md5, bcrypt.gensalt())
    bcrypt_cache = zglob.cache['bcrypt']
    bcrypt_cache[pw_bcrypt] = pw_md5 # cache pw

    safe_name = utils.get_safe_name(username)

    # fetch the users' country
    if (
        request.headers and
        (ip := request.headers.get('X-Real-IP', type=str)) is not None
    ):
        country = await utils.fetch_geoloc(ip)
    else:
        country = 'xx'

    async with app.state.services.database.connection() as db_cursor:
        # add to `users` table.
        await db_cursor.execute(
            'INSERT INTO users '
            '(name, safe_name, email, pw_bcrypt, country, creation_time, latest_activity) '
            'VALUES (:name, :safe_name, :email, :pw_bcrypt, :country, UNIX_TIMESTAMP(), UNIX_TIMESTAMP())',
            {
                "name":      username,
                "safe_name": safe_name,
                "email":     email,
                "pw_bcrypt": pw_bcrypt,
                "country":   country
            })

        user_id = await db_cursor.fetch_val(
            'SELECT id FROM users WHERE name = :safe_name',
            {"safe_name": safe_name})

        #TODO: Use execute_many here, it's faster.
        # add to `stats` table.
        for mode in (
            0,  # vn!std
            1,  # vn!taiko
            2,  # vn!catch
            3,  # vn!mania
            4,  # rx!std
            5,  # rx!taiko
            6,  # rx!catch
            8,  # ap!std
        ):
            await db_cursor.execute(
                'INSERT INTO stats '
                '(id, mode) VALUES (:id, :mode)',
                {"id": user_id, "mode": mode}
            )


    # user has successfully registered
    log(f"User <{username} ({user_id})> has successfully registered through website.", Ansi.GREEN)
    return await render_template('verify.html')

@frontend.route('/leaderboard')
@frontend.route('/lb')
@frontend.route('/leaderboard/<mode>/<sort>/<mods>')
@frontend.route('/lb/<mode>/<sort>/<mods>')
async def leaderboard(mode='std', sort='pp', mods='vn'):
    return await render_template('leaderboard.html', mode=mode, sort=sort, mods=mods)

@frontend.route('/u/<u>')
@frontend.route('/u/<u>/home')
@frontend.route('/u/<u>/<mode>')
@frontend.route('/u/<u>/<mode>/home')
async def profile(u:str=None, mode:int=None):
    #* User not specified
    if u == None:
        return await utils.flash_tohome('error', 'You must specify username or id')
    #* Update privs
    if 'authenticated' in session:
        await utils.updateSession(session)

    #* Get user
    u = await app.state.services.database.fetch_one(
        "SELECT id, name, priv, country, creation_time, "
        "latest_activity, preferred_mode, userpage_content, clan_id "
        "FROM users WHERE id=:u or name=:u",
        {"u": u}
    )
    if not u:
        return await utils.flash_tohome("error", "User not found") #switch to user specific 404
    u = dict(u)

    #! Get author priv and check if target is restricted
    is_staff = 'authenticated' in session and session['user_data']['is_staff']
    if not (u['priv'] & Privileges.NORMAL or is_staff):
        return (await render_template('404.html'), 404)

    u['customisation'] = utils.has_profile_customizations(u['id'])

    #* Check if mode, not specified. Set to user preferred (default: 0)
    if not mode:
        mode = u['preferred_mode']
    if int(mode) not in [0,1,2,3,4,5,6,8]:
        return await utils.flash_tohome("error", "Invalid mode") #switch to user specific 404

    #* Get stats
    s = await app.state.services.database.fetch_one(
        "SELECT * FROM stats WHERE id=:uid AND mode=:mode",
        {"uid": u['id'], "mode": mode}
    )
    s = dict(s)

    #* Format stuff
    s['acc'] = round(s['acc'], 2)
    s['rscore'] = "{:,}".format(s['rscore'])
    s['tscore'] = "{:,}".format(s['tscore'])
    u['register_dt'] = datetime.datetime.fromtimestamp(float(u['creation_time']))
    u['latest_activity_dt'] = datetime.datetime.fromtimestamp(float(u['latest_activity']))

    #Unnecessary checks :trolley:
    if u['userpage_content'] != None:
        u['userpage_content'] = md(u['userpage_content'])

    return await render_template('profile/home.html', user=u, mode=mode, stats=s, cur_page="home")


# profile customisation
BANNERS_PATH = Path.cwd() / 'zenith/.data/banners'
BACKGROUND_PATH = Path.cwd() / 'zenith/.data/backgrounds'
@frontend.route('/banners/<user_id>')
async def get_profile_banner(user_id: int):
    # Check if avatar exists
    for ext in ('jpg', 'jpeg', 'png', 'gif'):
        path = BANNERS_PATH / f'{user_id}.{ext}'
        if path.exists():
            return await send_file(path)

    return b'{"status":404}'


@frontend.route('/backgrounds/<user_id>')
async def get_profile_background(user_id: int):
    # Check if avatar exists
    for ext in ('jpg', 'jpeg', 'png', 'gif'):
        path = BACKGROUND_PATH / f'{user_id}.{ext}'
        if path.exists():
            return await send_file(path)

    return b'{"status":404}'

#! Settings
@frontend.route('/settings')
async def default_settings_redirect():
    return redirect('/settings/profile')

@frontend.route('/settings/profile')
async def settings_profile():
    #* Update privs
    if 'authenticated' in session:
        await utils.updateSession(session)
    else:
        return await flash_tohome("error", "You must be logged in to enter this page.")
    return await render_template('/settings/profile.html')

@frontend.route('/settings/profile/change_email', methods=['POST', 'GET'])
async def settings_profile_change_email():
    if 'authenticated' in session:
        await utils.updateSession(session)
    else:
        return await flash_tohome("error", "You must be logged in to enter this page.")

    # Get code from form
    form = await request.form
    new_email = form.get('new_email', type=str)
    passwd_txt = form.get('new_email-password', type=str)


    # Check password
    if not await validate_password(session['user_data']['id'], passwd_txt):
        return await flash('error', 'Invalid password, email unchanged.', 'settings/profile')

    # Check email
    old_email = await app.state.services.database.fetch_val(
        "SELECT email FROM users WHERE id=:uid",
        {"uid": session['user_data']['id']}
    )
    if new_email == old_email:
        return await flash('error', 'New email must be diffrent from previous one', 'settings/profile')

    email_used = await app.state.services.database.fetch_val('SELECT 1 FROM users WHERE email=:email', {'email': new_email})
    if email_used:
        return await flash('error', 'Email already in use', 'settings/profile')
    if not regexes.email.match(new_email):
        return await flash('error', 'Invalid email syntax.', 'settings/profile')

    await app.state.services.database.execute(
        "UPDATE users SET email=:new_email WHERE id=:uid",
        {"new_email": new_email, "uid": session['user_data']['id']}
    )
    redirect('/settings/profile')
    return await flash('success', 'Email changed successfully', 'settings/profile')

@frontend.route('/settings/profile/change_password', methods=['POST', 'GET'])
async def settings_profile_change_password():
    form = await request.form
    old_pwd = form.get('old_password', type=str)
    new_pwd = form.get('new_password', type=str)
    new_pwd_c = form.get('new_password_confirm', type=str)

    # Validate old password
    if not await validate_password(session['user_data']['id'], old_pwd):
        return await flash('error', 'Invalid password, password unchanged.', 'settings/profile')

    if len(new_pwd) < 8 or len(new_pwd) > 50:
        return await flash('error', 'New password must be longer than 8 characters and shorter than 50 characters.', 'settings/profile')
    if new_pwd != new_pwd_c:
        return await flash('error', 'New confirmed password is not the same as new password.', 'settings/profile')
    if new_pwd == old_pwd:
        return await flash('error', "New password must be diffrent from old password.", 'settings/profile')
    if len(set(new_pwd)) <= 3:
        return await render_template('register.html', message={"password": 'Password must have more than 3 unique characters.'})
    if new_pwd.lower() in zconfig.disallowed_passwords:
        return await render_template('register.html', message={"password": 'That password was deemed too simple.'})

    # Update password.
    pw_md5 = hashlib.md5(new_pwd.encode()).hexdigest().encode()
    pw_bcrypt = bcrypt.hashpw(pw_md5, bcrypt.gensalt())
    bcrypt_cache = zglob.cache['bcrypt']
    bcrypt_cache[pw_bcrypt] = pw_md5 # cache pw
    await app.state.services.database.execute(
        "UPDATE users SET pw_bcrypt=:new_pw_hashed",
        {'new_pw_hashed', pw_bcrypt}
    )

    # Log user out
    session.pop('authenticated', None)
    session.pop('user_data', None)

    return await flash_tohome('success', 'Password changed, please log in again.')

@frontend.route('/settings/customization')
async def settings_customizations():
    return await render_template('settings/customization.html')

@frontend.route('/settings/customization/avatar', methods=['POST'])
async def settings_avatar_post():
    #* Update privs
    if 'authenticated' in session:
        await utils.updateSession(session)
    else:
        return await flash_tohome("error", "You must be logged in to enter this page.")
    # constants

    if Privileges.BLOCK_AVATAR in Privileges(int(session['user_data']['id'])):
        return flash('errors', "You don't have privileges to change your avatar", 'settings/customization')
    AVATARS_PATH = f'{zconfig.path_to_gulag}.data/avatars'
    ALLOWED_EXTENSIONS = ['.jpeg', '.jpg', '.png']

    avatar = (await request.files).get('avatar')
    print(await request.files)
    # no file uploaded; deny post
    if avatar is None or not avatar.filename:
        return await flash('error', 'No image was selected!', 'settings/customization')

    filename, file_extension = os.path.splitext(avatar.filename.lower())

    # bad file extension; deny post
    if not file_extension in ALLOWED_EXTENSIONS:
        return await flash('error', 'The image you select must be either a .JPG, .JPEG, or .PNG file!', 'settings/customization')

    # remove old avatars
    for fx in ALLOWED_EXTENSIONS:
        if os.path.isfile(f'{AVATARS_PATH}/{session["user_data"]["id"]}{fx}'): # Checking file e
            os.remove(f'{AVATARS_PATH}/{session["user_data"]["id"]}{fx}')

    # avatar cropping to 1:1
    pilavatar = Image.open(avatar.stream)

    # avatar change success
    pilavatar = utils.crop_image(pilavatar)
    pilavatar.save(os.path.join(AVATARS_PATH, f'{session["user_data"]["id"]}{file_extension.lower()}'))
    return await flash('success', 'Your avatar has been successfully changed!', 'settings/customization')

#! Dedicated docs
@frontend.route('/docs/privacy_policy')
async def privacy_policy():
    return await render_template('privacy_policy.html')

#! Redirects
@frontend.route('/discord')
async def redirect_discord():
    return redirect(zconfig.discord_server)