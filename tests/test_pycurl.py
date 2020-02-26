from pyload.core.network.http.http_request import HTTPRequest
from pyload.core.network.cookie_jar import CookieJar, Cookie
import pycurl
from io import BytesIO
buffer = BytesIO()
header_buffer = BytesIO()
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

# request = HTTPRequest()
# cookie_jar = CookieJar()
# cookie = Cookie()
# cookie.domain = 'recaptcha.lw-rulez.de'
# cookie.name = 'test'
# cookie.value = 'bla'
# cookie_jar.add_cookie(cookie)
# request.load('http://recaptcha.lw-rulez.de/', cookies=cookie_jar, post={"foob": "bar"})
cookie_jar = CookieJar()
cookie_jar.add_key_value('kohanasession', 'fc25635fba647d16d68760164a7f87fdfa7431e1~4nr7prr2o2beqmlcbiididud10')
cookie_jar.add_key_value('compid', '37e69ff95d94aaa966d79c25e02c3f586bde911f~1657556BDA125B58A6C7AD5C3A73CF5E')
cookie_jar.add_key_value('user_lang', 'en')
cookie_jar.add_key_value('_gaid_variant', '3b0d3f3778f4103e1fdf0b877c41b21830178ad0~1')
cookie_jar.add_key_value('file_marker', '77fa060715f25ef357f3bdd37886be97e0fa323c~6gpwt75gywzv')
cookie_jar.add_key_value('refuid', '180e47d44e9985f5c4d6d94ca828ac86e3081382~D33F45075D72FEFA6F332C95E493B1FD')

r='03AERD8Xo7dOSwq1yhdrb_A4gg57zxOWuVb0UQV1Xwn036WO_zao1XZSYIspFRMEwITr_Mq_V2KNB9Bhji1VcM_UZXzNmmxURqifMxP0tE_fvEw8kAkSRqsW3UgV9g3GHBb3lfsBjGEYXUTf7xTpuhUmmWoagXnLo0TPExUyJu3MR_UDbehsEbI0MCjlZctBlYCgXi7sgMm_oFniCmugvCiO4_HfWfiECYgqki3aJi0LxLFM4XEvZ74o8HbXtSIHdHA5BB0eB-rWsCJg60YHZ_Stl7qYrtW_Uoj4-WPrcPgklJTuXu7DR56SJpNwjr0P7fxwUZ0-0w5PkKEwScQ-JtbC-5NbjLyANLSuqFS8zO0O3vFoj_H6SfVMiMr3dRlymGy12QakWFgpeb'
c = pycurl.Curl()
c.setopt(c.URL, 'https://turbobit.net/download/free/6gpwt75gywzv')
c.setopt(c.POSTFIELDS, 'captcha_type=recaptcha2&captcha_subtype=&g-recaptcha-response='+r)
c.setopt(c.USERAGENT, "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:75.0) Gecko/20100101 Firefox/75.0")
c.setopt(c.WRITEDATA, buffer)
c.setopt(c.WRITEHEADER, header_buffer)
c.setopt(c.COOKIELIST, cookie_jar.get_cookie_list())
c.perform()
c.close()

header = header_buffer.getvalue()
print(header.decode('utf-8'))
body = buffer.getvalue()
print(body.decode('utf-8'))