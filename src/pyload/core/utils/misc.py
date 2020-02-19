# -*- coding: utf-8 -*-
# AUTHOR: vuolter

import random
import socket
import string

import requests_html
from binascii import unhexlify
from cryptography.fernet import Fernet
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


def add_crypted2(js_key, *args, api, jk, encrypted, package):
    from hashlib import md5
    from base64 import b64decode
    from base64 import b64encode

    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    from Crypto.Util.Padding import pad, unpad

    class AESCipher:
        def __init__(self, key):
            self.key = md5(key.encode('utf8')).digest()

        def encrypt(self, data):
            iv = get_random_bytes(AES.block_size)
            self.cipher = AES.new(self.key, AES.MODE_CBC, iv)
            return b64encode(iv + self.cipher.encrypt(pad(data.encode('utf-8'),
                                                          AES.block_size)))

        def decrypt(self, data):
            raw = b64decode(data)
            self.cipher = AES.new(self.key, AES.MODE_CBC, raw[:AES.block_size])
            return unpad(self.cipher.decrypt(raw[AES.block_size:]), AES.block_size)

    def gen_key(key):
        offset = 0
        return_key = bytearray(key)
        while len(return_key) < 32:
            return_key.append(return_key[offset % len(key)])
            offset += 1

        return return_key

    try:
        key = base64.urlsafe_b64encode(gen_key(base64.b16decode(js_key)))

        obj = Fernet(key)
        urls = obj.decrypt(encrypted).replace("\x00", "").replace("\r", "").split("\n")
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