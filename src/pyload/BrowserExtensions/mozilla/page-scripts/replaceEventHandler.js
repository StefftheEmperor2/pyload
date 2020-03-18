    EventTarget.prototype.realAddEventListener = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function(a,b,c)
    {
        console.log('add event handler ', this, a);
        this.realAddEventListener(a,b,c);

        if (!this.lastListenerInfo)
        {
            this.lastListenerInfo = [];
        };
        this.lastListenerInfo.push({a : a, b : b , c : c});
    };
    console.log('replaced event handler');

    EventTarget.prototype.clearEventListeners = function(a){
        if( ! this.lastListenerInfo)
        {
            this.eventListenerList = [];
        }

        var el = this.getEventListeners(a);

        for (var i = el.length - 1; i >= 0; --i)
        {
            var ev = el[i];
            this.removeEventListener(ev.a, ev.b, ev.c);
        }
    };

    EventTarget.prototype.realRemoveEventListener = Element.prototype.removeEventListener;
    EventTarget.prototype.removeEventListener = function(a,b,c) {
        if(c==undefined)
        {
            c=false;
        }
        this.realRemoveEventListener(a,b,c);
        if ( ! this.lastListenerInfo)
        {
            this.lastListenerInfo = [];
        }

        // Find the event in the list
        for (var i=0;i<this.lastListenerInfo.length;i++)
        {
            if(this.lastListenerInfo[i].a==a
                && this.lastListenerInfo[i].b==b
                && this.lastListenerInfo[i].c==c)
            {
                this.lastListenerInfo.splice(i, 1);
                break;
            }
        }
  };

  EventTarget.prototype.getEventListeners = function(a)
  {
    if (!this.lastListenerInfo)
    {
        this.lastListenerInfo = [];
    }

    if (a==undefined)
    {
        return this.lastListenerInfo;
    }
    else
    {
        let list = [];
        for (let i=0;i<this.lastListenerInfo.length;i++)
        {
            if (this.lastListenerInfo[i].a === a)
            {
                list.push(this.lastListenerInfo[i]);
            }
        }

        return list;
    }

    return this.eventListenerList[a];
  };