# -*- coding: utf-8 -*-
# AUTHOR: vuolter

import traceback
from ast import literal_eval
from itertools import chain
from urllib.parse import unquote

import flask
from flask.json import jsonify

from ..helpers import clear_session, login_required, set_session, parse_query
from pyload.core.api import MethodNotExistsException
bp = flask.Blueprint("api", __name__, url_prefix="/api")


# accepting positional arguments, as well as kwargs via post and get
# @bottle.route(
# r"/api/<func><args:re:[a-zA-Z0-9\-_/\"\'\[\]%{},]*>")
@login_required("ALL")
@bp.route("/<func>", methods=["GET", "POST"], endpoint="rpc")
@bp.route("/<func>?=<args>", methods=["GET", "POST"], endpoint="rpc")
# @apiver_check
def rpc(func, args=None):

    api = flask.current_app.config["PYLOAD_API"]
    s = flask.session
    if not api.is_authorized(func, {"role": s["role"], "permission": s["perms"]}):
        return "Unauthorized", 401

    if args is None:
        args = []
    else:
        args = args.split(",")
    kwargs = {}

    try:
        form_items = flask.request.form.items()
    except Exception:
        form_items = {}

    for x, y in chain(flask.request.args.items(), form_items):
        kwargs = parse_query(kwargs, x, y)

    try:
        response = call_api(func, *args, **kwargs)
    except MethodNotExistsException as exc:
        response = "Not found", 404
    except Exception as exc:
        api.pyload.log.error(exc)
        response = jsonify(error=exc, traceback=traceback.format_exc()), 500

    return response


def call_api(func, *args, **kwargs):
    api = flask.current_app.config["PYLOAD_API"]

    if func.startswith("_"):
        flask.flash(f"Invalid API call '{func}'")
        return "Forbidden", 403

    if hasattr(api, func):
        result = getattr(api, func)(
            *args,
            **kwargs
        )
    else:
        raise MethodNotExistsException(func)

    # null is invalid json response
    return jsonify(result or True)


@bp.route("/login", methods=["POST"], endpoint="login")
# @apiver_check
def login():
    user = flask.request.form["username"]
    password = flask.request.form["password"]

    api = flask.current_app.config["PYLOAD_API"]
    user_info = api.check_auth(user, password)

    if not user_info:
        return jsonify(False)

    s = set_session(user_info)
    flask.flash("Logged in successfully")

    return jsonify(s)


@bp.route("/logout", endpoint="logout")
# @apiver_check
def logout():
    # logout_user()
    clear_session()
    return jsonify(True)
