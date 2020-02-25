from pyload.core.network.http.http_request import HTTPRequest
from pyload.core.network.cookie_jar import CookieJar, Cookie

request = HTTPRequest()
cookie_jar = CookieJar()
cookie = Cookie()
cookie.domain = 'recaptcha.lw-rulez.de'
cookie.name = 'test'
cookie.value = 'bla'
cookie_jar.add_cookie(cookie)
request.load('http://recaptcha.lw-rulez.de/', cookies=cookie_jar)
