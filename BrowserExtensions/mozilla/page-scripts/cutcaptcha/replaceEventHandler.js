    EventTarget.prototype.realAddEventListener = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function(a,b,c)
    {
        console.log('add event handler');
        this.realAddEventListener(a,b,c);

        if(!this.lastListenerInfo){this.lastListenerInfo = new Array()};
        this.lastListenerInfo.push({a : a, b : b , c : c});
    };
    console.log('replaced event handler');