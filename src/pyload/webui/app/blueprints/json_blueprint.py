# -*- coding: utf-8 -*-
# AUTHOR: vuolter

import os

import flask
import json
from flask.json import jsonify

from pyload.core.utils import format

from ..helpers import login_required, render_template, parse_query
from pyload.core.network.cookie_jar import CookieJar
from pyload.core.network.cookie_jar import Cookie
bp = flask.Blueprint("json", __name__, url_prefix="/json")


def format_time(seconds):
    seconds = int(seconds)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


@bp.route("/status", methods=["GET", "POST"], endpoint="status")
# @apiver_check
@login_required("LIST")
def status():
    api = flask.current_app.config["PYLOAD_API"]
    data = api.status_server()
    return jsonify(data)


@bp.route("/links", methods=["GET", "POST"], endpoint="links")
# @apiver_check
@login_required("LIST")
def links():
    api = flask.current_app.config["PYLOAD_API"]
    try:
        links = api.status_downloads()
        ids = []
        for link in links:
            ids.append(link["fid"])

            if link["status"] == 12:
                formatted_eta = link["format_eta"]
                formatted_speed = format.speed(link["speed"])
                link["info"] = f"{formatted_eta} @ {formatted_speed}"

            elif link["status"] == 5:
                link["percent"] = 0
                link["size"] = 0
                link["bleft"] = 0
                link["info"] = api._("waiting {}").format(link["format_wait"])
            else:
                link["info"] = ""

        return jsonify(links=links, ids=ids)

    except Exception as exc:
        flask.abort(500)

    return jsonify(False)


@bp.route("/packages", endpoint="packages")
# @apiver_check
@login_required("LIST")
def packages():
    api = flask.current_app.config["PYLOAD_API"]
    try:
        data = api.get_queue()

        for package in data:
            package["links"] = []
            for file in api.get_package_files(package["id"]):
                package["links"].append(api.get_file_info(file))

        return jsonify(data)

    except Exception:
        flask.abort(500)

    return jsonify(False)


@bp.route("/package", endpoint="package")
# @apiver_check
@login_required("LIST")
def package():
    api = flask.current_app.config["PYLOAD_API"]
    request_data = {}
    for key, value in flask.request.args.items():
        request_data = parse_query(request_data, key, value)

    id = request_data['id']
    try:
        data = api.get_package_data(id)

        tmp = data["links"]
        tmp.sort(key=lambda entry: entry["order"])

        links_data = []
        for link_item in tmp:
            link_data = dict(link_item)
            del link_data['format_size']
            links_data.append(link_data)
        data["links"] = links_data
        return jsonify(data)

    except Exception as e:
        flask.abort(500)

    return jsonify(False)


# NOTE: 'ids' is a string
@bp.route("/package_order", endpoint="package_order")
# @apiver_check
@login_required("ADD")
def package_order():
    api = flask.current_app.config["PYLOAD_API"]
    try:
        pid = flask.request.args['id']
        pos = flask.request.args['order']
        api.order_package(int(pid), int(pos))
        return jsonify(response="success")
    except Exception:
        flask.abort(500)

    return jsonify(False)


@bp.route("/abort_link", endpoint="abort_link")
# @apiver_check
@login_required("DELETE")
def abort_link(id):
    api = flask.current_app.config["PYLOAD_API"]
    try:
        api.stop_downloads([id])
        return jsonify(response="success")
    except Exception:
        flask.abort(500)

    return jsonify(False)


# NOTE: 'ids' is a string
@bp.route("/link_order", endpoint="link_order")
# @apiver_check
@login_required("ADD")
def link_order():
    api = flask.current_app.config["PYLOAD_API"]
    try:
        pid = flask.request.args['lid']
        pos = flask.request.args['new_index']
        api.order_file(int(pid), int(pos))
        return jsonify(response="success")
    except Exception:
        flask.abort(500)

    return jsonify(False)


@bp.route("/add_package", methods=["POST"], endpoint="add_package")
# @apiver_check
@login_required("ADD")
def add_package():
    api = flask.current_app.config["PYLOAD_API"]

    name = flask.request.form.get("add_name", "New Package").strip()
    queue = int(flask.request.form["add_dest"])
    links = flask.request.form["add_links"].split("\n")
    pw = flask.request.form.get("add_password", "").strip("\n\r")

    try:
        f = flask.request.files["add_file"]

        if not name or name == "New Package":
            name = f.name

        fpath = os.path.join(
            api.get_config_value("general", "storage_folder"), "tmp_" + f.filename
        )
        f.save(fpath)
        links.insert(0, fpath)

    except Exception:
        pass

    urls = [url for url in links if url.strip()]
    pack = api.add_package(name, urls, queue)
    if pw:
        data = {"password": pw}
        api.set_package_data(pack, data)

    return jsonify(True)


@bp.route("/move_package", endpoint="move_package")
# @apiver_check
@login_required("MODIFY")
def move_package():
    api = flask.current_app.config["PYLOAD_API"]
    dest = int(flask.request.args['target'])
    id = int(flask.request.args['id'])
    try:
        api.move_package(dest, id)
        return jsonify(response="success")
    except Exception:
        flask.abort(500)

    return jsonify(False)


@bp.route("/edit_package", methods=["POST"], endpoint="edit_package")
# @apiver_check
@login_required("MODIFY")
def edit_package():
    api = flask.current_app.config["PYLOAD_API"]
    try:
        id = int(flask.request.form["pack_id"])
        data = {
            "name": flask.request.form["pack_name"],
            "folder": flask.request.form["pack_folder"],
            "password": flask.request.form["pack_pws"],
        }

        api.set_package_data(id, data)
        return jsonify(response="success")

    except Exception:
        flask.abort(500)

    return jsonify(False)


@bp.route("/set_captcha", methods=["GET", "POST"], endpoint="set_captcha")
# @apiver_check
@login_required("ADD")
def set_captcha():
    api = flask.current_app.config["PYLOAD_API"]

    if flask.request.method == "POST":
        tid = int(flask.request.form["cap_id"])
        result = json.loads(flask.request.form["cap_result"])
        data = result['data']
        cookie_jar_string = result['cookie']
        domain = result['domain']

        cookie_jar_items = cookie_jar_string.split(';')
        cookie_jar = CookieJar()
        for cookie_jar_item in cookie_jar_items:
            cookie_jar_item_key_value_pair = cookie_jar_item.split('=')
            cookie_key = cookie_jar_item_key_value_pair[0].strip()
            cookie_value = cookie_jar_item_key_value_pair[1].strip()
            cookie = Cookie()
            cookie.name = cookie_key
            cookie.value = cookie_value
            cookie.domain = domain
            cookie_jar.add_cookie(cookie)

        api.set_captcha_result(tid, data, cookie_jar)

    task = api.get_captcha_task()
    if task.tid >= 0:
        data = {
            "captcha": True,
            "id": task.tid,
            "params": task.data,
            "result_type": task.result_type,
        }
    else:
        data = {"captcha": False}

    return jsonify(data)


@bp.route("/load_config", endpoint="load_config")
# @apiver_check
@login_required("SETTINGS")
def load_config():
    conf = None
    api = flask.current_app.config["PYLOAD_API"]
    category = flask.request.args.get('category')
    section = flask.request.args.get('section')
    if category == "general":
        conf = api.get_config_dict()
    elif category == "plugin":
        conf = api.get_plugin_config_dict()

    for key, option in conf[section].items():
        if key in ("desc", "outline"):
            continue

        if ";" in option["type"]:
            option["list"] = option["type"].split(";")

    return render_template("settings_item.html", category=category, skey=section, section=conf[section])


@bp.route("/save_config", methods=["POST"], endpoint="save_config")
# @apiver_check
@login_required("SETTINGS")
def save_config():
    api = flask.current_app.config["PYLOAD_API"]
    form_data = flask.request.form.items()
    for key, value in flask.request.form.items():
        if key == 'category':
            category = value
            continue
        try:
            section, option = key.split("|")
        except Exception:
            continue

        if category == "general":
            category = "core"

        api.set_config_value(section, option, value, category)

    return jsonify(True)


@bp.route("/add_account", methods=["POST"], endpoint="add_account")
# @apiver_check
@login_required("ACCOUNTS")
# @fresh_login_required
def add_account():
    api = flask.current_app.config["PYLOAD_API"]

    login = flask.request.form["account_login"]
    password = flask.request.form["account_password"]
    type = flask.request.form["account_type"]

    api.update_account(type, login, password)
    return jsonify(True)


@bp.route("/update_accounts", methods=["POST"], endpoint="update_accounts")
# @apiver_check
@login_required("ACCOUNTS")
# @fresh_login_required
def update_accounts():
    deleted = []  #: dont update deleted accs or they will be created again
    api = flask.current_app.config["PYLOAD_API"]

    for name, value in flask.request.form.items():
        value = value.strip()
        if not value:
            continue

        tmp, user = name.split(";")
        plugin, action = tmp.split("|")

        if (plugin, user) in deleted:
            continue

        if action == "password":
            api.update_account(plugin, user, value)
        elif action == "time" and "-" in value:
            api.update_account(plugin, user, options={"time": [value]})
        elif action == "limitdl" and value.isdigit():
            api.update_account(plugin, user, options={"limit_dl": [value]})
        elif action == "delete":
            deleted.append((plugin, user))
            api.remove_account(plugin, user)

    return jsonify(True)


@bp.route("/change_password", methods=["POST"], endpoint="change_password")
# @apiver_check
# @fresh_login_required
@login_required("ACCOUNTS")
def change_password():
    api = flask.current_app.config["PYLOAD_API"]

    user = flask.request.form["user_login"]
    oldpw = flask.request.form["login_current_password"]
    newpw = flask.request.form["login_new_password"]

    done = api.change_password(user, oldpw, newpw)
    if not done:
        return "Wrong password", 500

    return jsonify(True)
