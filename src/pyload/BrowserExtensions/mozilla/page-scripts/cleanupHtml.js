(function () {
    let i, k, elem, innerElem, body;
    for (i=0;i<document.children[0].childElementCount;i++)
    {
        elem = document.children[0].children[i];
        if (elem.tagName == 'body')
        {
            body = elem;
        }
        for (k=0;k<elem.childElementCount;k++)
        {
            innerElem = elem.children[k];
            elem.removeChild(innerElem);
            console.log('remove elem ', innerElem);
        }
    }
    console.log('HTML cleared');
})();