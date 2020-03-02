# -*- coding: utf-8 -*-
# AUTHOR: vuolter

import random
import socket
import string

import requests_html
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64

def random_string(length):
    seq = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.choice(seq) for _ in range(length))


def is_plural(value):
    try:
        n = abs(float(value))
        return n == 0 or n > 1
    except ValueError:
        return value.endswith("s")  # TODO: detect uncommon plurals


def eval_js(script, *args, **kwargs):
    return requests_html.HTML(html="""<html></html>""").render(script=script, reload=False)


def accumulate(iterable, to_map=None):
    """
    Accumulate (key, value) data to {value : [key]} dictionary.
    """
    if to_map is None:
        to_map = {}
    for key, value in iterable:
        to_map.setdefault(value, []).append(key)
    return to_map


def reversemap(obj):
    """
    Invert mapping object preserving type and ordering.
    """
    return obj.__class__(reversed(item) for item in obj.items())


def forward(source, destination, buffering=1024):
    try:
        rawdata = source.recv(buffering)
        while rawdata:
            destination.sendall(rawdata)
            rawdata = source.recv(buffering)
    finally:
        destination.shutdown(socket.SHUT_WR)

def aes_decrypt(key, encrypted):
    backend = default_backend()
    cipher = Cipher(algorithms.AES(key), modes.CBC(key), backend=backend)
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(encrypted) + decryptor.finalize()
    return decrypted.decode('utf-8')


def add_crypted2(js_key, *args, api, encrypted, package):
    try:
        key_decoded = base64.b16decode(js_key)

        decrypted = aes_decrypt(key_decoded, base64.b64decode(encrypted))
        urls = decrypted.replace("\x00", "").replace("\r", "").split("\n")
    except Exception as exc:
        return f"Could not decrypt key {exc}", 500

    urls = [url for url in urls if url.strip()]

    try:
        if package:
            api.add_package(package, urls, 0)
        else:
            api.generate_and_add_packages(urls, 0)

    except Exception:
        return "failed can't add", 500
    else:
        return "success\r\n"