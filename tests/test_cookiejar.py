import pyload.core.network.cookie_jar as cookie_jar

class Test_CookieJar:
    def test_cookiejar(self):
        cookie_string = "lang=de; PHPSESSID=4aipvnat5lopr6t1roodg7dgu3; mid=ecbcd825-b379-4550-8c44-93680fb82aae; " \
                        "ab=1582627075; ac=2; ha=1; haad=1; haac=1; ptxx=1; WaynePop30=1"
        cookie_jar.factory_by_string(cookie_string)
