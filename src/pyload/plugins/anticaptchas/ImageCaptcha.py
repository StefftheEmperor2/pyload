from pyload.plugins.base.captcha import BaseCaptcha


class ImageCaptcha(BaseCaptcha):

    def recognize(self, image):
        raise NotImplementedError
