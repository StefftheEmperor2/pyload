
window.cgpyload = function()
{
    this.setSiteKey = function(paramSiteKey)
    {
        window.gpyload.data.sitekey = paramSiteKey;
        let event = new CustomEvent('pyload.siteKeySet', {"detail": window.gpyload.data.sitekey });
        window.dispatchEvent(event);
    }

    this.getSiteKey = function()
    {
        return window.gpyload.data.sitekey;
    }

    this.activated = function()
    {
        let event = new CustomEvent('pyload.activated');
        window.dispatchEvent(event);
    }

    this.submitResponse = function(response)
    {
        let event = new CustomEvent('pyload.submitResponse', { "detail": response });
        window.dispatchEvent(event);
    }
}
window.gpyload = {};
window.gpyload.getInstance = function()
{
    let gpyloadInstance = undefined;
    if (typeof window.gpyload.instance == 'undefined')
    {
        gpyloadInstance = new cgpyload();
        window.gpyload.instance = gpyloadInstance;
        window.addEventListener('pyload.setSiteKey', function(event) {
            gpyloadInstance.setSiteKey(event.detail);
        });
    }
    else
    {
        gpyloadInstance = window.gpyload.instance;
    }
    return gpyloadInstance;
};

window.gpyload.data = {
    "sitekey": null
};

window.pyloadCaptchaOnLoadCallback = function()
{
    console.log('captcha loaded');
    grecaptcha.render(
        "captchadiv",
        {
            "size": "compact",
            "sitekey": window.gpyload.getInstance().getSiteKey(),
            "callback": function() {
                let recaptchaResponse = grecaptcha.getResponse(); // get captcha response
                window.gpyload.getInstance().submitResponse(recaptchaResponse);
            }
        }
    );
    window.gpyload.getInstance().activated();
};

window.gpyload.getInstance();