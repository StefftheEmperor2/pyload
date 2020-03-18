(function()
{
    let observer = new MutationObserver(function(mutationsList)
    {
        console.log('mutation observed');
        let event = new CustomEvent('pyload.mutationObserved');
        window.dispatchEvent(event);
    });

    let observerTarget = window.document.querySelector('body');
    observer.observe(observerTarget,
    {
        attributes:true,
        attributeOldValue:false,
        characterData:true,
        characterDataOldValue:false,
        childList:true,
        subtree:true
    });

    console.log('registered mutationobserver on ', observerTarget)
})();
