from pyload.core.network.http.http_request import HTTPRequest
from pyload.core.network.cookie_jar import CookieJar, Cookie
from pyload.plugins.downloaders.TurbobitNet import TurbobitNet
from pyload.core.datatypes.pyfile import PyFile
from pyload.core.managers.file_manager import FileManager
from pyload.core import Core
import pycurl
from io import BytesIO
from pyload.core.network.request_factory import RequestFactory
import re
from urllib.parse import unquote_plus

class CoreMock(Core):
    def __init__(self):
        self._ = lambda x: x
        self._init_config('/tmp/pyload', '/tmp/pyload', '/tmp/pyload', 2)
        self.req = self.request_factory = RequestFactory(self)
        self._init_api()
        self._init_log()
        pass

buffer = BytesIO()
header_buffer = BytesIO()
core = CoreMock()

file_manager = FileManager(core)
pyfile = PyFile(file_manager, 0, '', '', 0, 0, None, None, None, 0)
plugin = TurbobitNet(pyfile)
cookie_jar = plugin.cookie_jar
#
# c = pycurl.Curl()
# c.setopt(c.URL, 'https://turbobit.net/6gpwt75gywzv.html')
# c.setopt(c.USERAGENT, "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:75.0) Gecko/20100101 Firefox/75.0")
# c.setopt(c.WRITEDATA, buffer)
# c.setopt(c.WRITEHEADER, header_buffer)
# c.perform()
# c.close()
#
# header = header_buffer.getvalue()
# print(header.decode('utf-8'))
#
# body = buffer.getvalue()
# print(body.decode('utf-8'))

request = HTTPRequest()

r = '03AERD8XpxWcb3J9D6otuJNPJ5kl6VDgNKeekbUJdZHMX4iEWogAEMTz2zyP-D-rzxOsOwrX7onAzO0Wv6m8XlNHmgWF5Uwhuu9zs8cCaGUNTlhIfJofgd9FoXYZgzilnqGT5gBaULLB0F-7tKnEmJw4jJIDKekuJCcaCPW17xj1ciVdkusi4lCZxvREZ6N3SG2shaZ2brv6rhpfNjEKQwzldZLiuY1s6-2ZKj_jgng2OLmf49FUuNNYURbbdHtw6YhD_xHHtAgXQ3m-lKvw640Hf7aiLXWILURK8akZ9d4mN49kncBzHPit0ZS_58A-KelvsRuYXFtgMk7V2K9hiWG3d7hxuPxBTrFASWciTb9dzEmnPNGJh0OHnuTBhroosrki7mgvfSI6HD'

post = {
    "captcha_type": "recaptcha2",
    "captcha_subtype": "",
    "g-recaptcha-response": r
}

# cookie_jar = CookieJar()
# cookie = Cookie()
# cookie.domain = 'recaptcha.lw-rulez.de'
# cookie.name = 'test'
# cookie.value = 'bla'
# cookie_jar.add_cookie(cookie)
# request.load('http://recaptcha.lw-rulez.de/', cookies=cookie_jar, post={"foob": "bar"})
"""
cookie_jar.add_key_value('kohanasession', unquote_plus('3b31b09fcb70fee77de937220b767045bd2c3284%7Es5i33qs1049ok3bnjj7gvu8ql6'))
cookie_jar.add_key_value('compid', unquote_plus('db8a50a735f8f13b1ed9354f5264b14c479b34c0%7E247EF0EE0A0090AD03A1E97E18E30197'))
cookie_jar.add_key_value('user_lang', 'en')
cookie_jar.add_key_value('file_marker', unquote_plus('a1eae0906bd35c74de1bdeda4327d43b273f7004%7E6gpwt75gywzv'))
cookie_jar.add_key_value('refuid', unquote_plus('4658206b362392aa122e2edfe9eb67689531b800%7ED33F45075D72FEFA6F332C95E493B1FD'))
"""
"""
plugin.load(
    url='https://turbobit.net/6gpwt75gywzv.html',
    cookies=cookie_jar
    )
plugin.load(
    url='https://turbobit.net/6gpwt75gywzv.html',
    cookies=cookie_jar
    )
response = plugin.load(
    url='https://turbobit.net/download/free/6gpwt75gywzv',
    cookies=cookie_jar
    )
sess = cookie_jar['kohanasession']
"""
response = plugin.load(
    url='https://turbobit.net/download/free/6gpwt75gywzv',
    post=post,
    cookie_jar=cookie_jar
    )
#new_sess = cookie_jar['kohanasession']
#if sess != new_sess:
#    print('session!?')

print(response)

err = re.search(r"Incorrect, try again!", response)
if err is not None:
    print('captcha incorrect')
else:
    m = re.search(r"minLimit : (.+?),", response)
    if m is None:
        print("minLimit pattern not found")
    else:
        print('all ok')

"""c = pycurl.Curl()
c.setopt(c.URL, 'https://turbobit.net/download/free/6gpwt75gywzv')
c.setopt(c.POSTFIELDS, 'captcha_type=recaptcha2&captcha_subtype=&g-recaptcha-response='+r)
c.setopt(c.USERAGENT, "Mozilla/5.0 (X11; Linux x86_64; rv:75.0) Gecko/20100101 Firefox/75.0")
c.setopt(c.WRITEDATA, buffer)
c.setopt(c.WRITEHEADER, header_buffer)
c.setopt(c.COOKIELIST, cookie_jar.get_cookie_list())
c.perform()
c.close()

header = header_buffer.getvalue()
print(header.decode('utf-8'))
body = buffer.getvalue()
print(body.decode('utf-8'))"""

"""
cookie_jar.set_domain('.recaptcha.lw-rulez.de')
response = plugin.load(url='http://recaptcha.lw-rulez.de/', cookies=cookie_jar)
print(response)
response = plugin.load(url='http://recaptcha.lw-rulez.de/', cookies=cookie_jar, post={"bla": "test", "fooäöü": "baröä"})
print(response)
"""

