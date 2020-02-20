from Crypto.Cipher import AES
import base64
import binascii
from pyload.core.utils.misc import aes_decrypt
class TestClickNLoad:

    @staticmethod
    def base16encode(key):
        return_key = bytearray()
        for char in key:
            return_key += base64.b16encode(ord(char).to_bytes(1, byteorder='little'))
        return bytes(return_key)

    @staticmethod
    def base16decode(key):
        return key.encode('utf-8')

    @staticmethod
    def bytetointarray(bytes):
        integers = []
        for byte in bytes:
            integers.append(int.from_bytes([byte], byteorder='big'))

        return integers

    def test_encryption(self):
        key = '1234567890987654'
        transmit_key = base64.urlsafe_b64encode(self.base16encode(key))
        link = 'http://rapidshare.com/files/285626259/jDownloader.dmg\r\nhttp://rapidshare.com/files/285622259/jDownloader2.dmg'
        obj = Fernet(transmit_key)
        encrypted = obj.encrypt(link.encode('utf-8'))

    def test_clicknload(self):
        key = '31323334353637383930393837363534'
        encrypted = 'DRurBGEf2ntP7Z0WDkMP8e1ZeK7PswJGeBHCg4zEYXZSE3Qqxsbi5EF1KosgkKQ9SL8qOOUAI+eDPFypAtQS9A=='

        key_decoded = base64.b16decode(key)

        key_decrypted = aes_decrypt(key_decoded, base64.b64decode(encrypted))

        urls = key_decrypted.replace("\x00", "").replace("\r", "").split("\n")
        assert urls == ['http://rapidshare.com/files/285626259/jDownloader.dmg']
