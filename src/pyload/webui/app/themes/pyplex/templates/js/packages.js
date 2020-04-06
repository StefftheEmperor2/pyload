{% autoescape true %}

$(function () {
    var pyload = $(document).data('pyload');
    $('#package-list').each(function () {
        var $elem = $(this),
            pUI = $elem.data('pUI');

        if ( ! pUI)
        {
            pUI = new PackageUI($elem.data('target'), pyload);
            $elem.data('pUI', pUI);
        }

    });
});

function PackageUI (type, pyload)
{
    var packages = [];
    var thisObject;
    this.initialize = function(type) {
        thisObject = this;
        this.type = type;

        $("#del_finished").click(this.deleteFinished);
        $("#restart_failed").click(this.restartFailed);
        this.parsePackages();

    };

    this.parsePackages = function () {
       var $packageList = $("#package-list");
       $packageList.children("li").each(function(ele) {
            var match = this.id.match(/[0-9]+/), id;
            id = match[0];
            packages.push(new Package(thisObject, id, $(this)));
        });
        $packageList.sortable({
            handle: ".progress",
            axis: "y",
            cursor: "grabbing",
            start: function(event, ui) {
                $(this).attr('data-previndex', ui.item.index());
            },
            stop: function(event, ui) {
                var newIndex = ui.item.index();
                var oldIndex = $(this).attr('data-previndex');
                $(this).removeAttr('data-previndex');
                if (newIndex === oldIndex) {
                    return false;
                }
                var id = ui.item.data('pid');
                var order = newIndex;
                indicateLoad();
                $.get("/json/package_order", {"id": id, "order": order}, function () {
                    indicateFinish();
                    return true;
                }).fail(function () {
                    indicateFail();
                    return false;
                });
          }
        });
    };

    this.deleteFinished = function () {
        indicateLoad();
        $.get("/api/delete_finished", function(data) {
            if (data.length > 0) {
                window.location.reload();
            } else {
                $.each(packages, function (pack) {
                    this.close();
                });
            }
            indicateSuccess();
        }).fail(function () {
            indicateFail();
        });
    };

    this.restartFailed = function () {
        indicateLoad();
        $.get("/api/restart_failed", function(data) {
            if (data.length > 0) {
                $.each(packages,function(pack) {
                    this.close();
                });
            }
            indicateSuccess();
        }).fail(function () {
            indicateFail();
        });
    };

    this.get_pyload = function()
    {
        return pyload;
    };

    this.humanFileSize = function(bytes, si)
    {
        return this.get_pyload().humanFileSize(bytes, si)
    };

    this.initialize(type);
}

function File(package, file)
{
    var thisObject = this,
        $ul, $li;

    this.get_icon_class = function(status)
    {
        if (status === 0)
            file_icon = 'glyphicon glyphicon-ok';
        else if (status === 2 || file.status === 3)
            file_icon = 'glyphicon glyphicon-time';
        else if (status ===  9 || file.status === 1)
            file_icon = 'glyphicon glyphicon-ban-circle';
        else if (status === 5)
            file_icon = 'glyphicon glyphicon-time';
        else if (status === 8)
            file_icon = 'glyphicon glyphicon-exclamation-sign';
        else if (status === 4)
            file_icon = 'glyphicon glyphicon-arrow-right';
        else if (status ===  11 || file.status === 13)
            file_icon = 'glyphicon glyphicon-cog';
        else
            file_icon = 'glyphicon glyphicon-cloud-download';

            return file_icon
    };
    this.event_handler = function(event)
    {
        data = JSON.parse(event.data);
        if (data.message == 'update_queue_file' && data.payload.id == file.fid)
        {
            $li.find('.child_secrow .child_status.status_message').text(data.payload.status_name);
            $li.find('.child_status .glyphicon').removeClass('glyphicon-ok')
                .removeClass('glyphicon-time')
                .removeClass('glyphicon-ban-circle')
                .removeClass('glyphicon-exclamation-sign')
                .removeClass('glyphicon-arrow-right')
                .removeClass('glyphicon-cog')
                .removeClass('glyphicon-cloud-download')
                .addClass(thisObject.get_icon_class(data.payload.status))
        }
    };

    var initialize = function()
    {
        $ul = $("#sort_children_" + package.get_id())
        $li = $("<li></li>");
        $li.css("margin-left",0);

        file_icon = thisObject.get_icon_class(file.status)

        var $html = $("<span class='child_status'><span style='margin-right: 2px;color: #f9be03;' class='" + file_icon + "'></span></span>\n" +
                   "<span style='font-size: 16px; font-weight: bold;'><a href='" + file.url + "' target='_blank'>" + file.name + "</a></span><br/>" +
                   "<div class='child_secrow' style='margin-left: 21px; margin-bottom: 7px; border-radius: 4px;'>" +
                   "<span class='child_status status_message' style='font-size: 12px; color:#eee; padding-left: 5px;'>" + file.statusmsg + "</span>&nbsp;" + file.error + "&nbsp;" +
                   "<span class='child_status status_size' style='font-size: 12px; color:#eee;'>" + thisObject.humanFileSize(file.size) + "</span>" +
                   "<span class='child_status status_plugin' style='font-size: 12px; color:#eee;'> " + file.plugin + "</span>&nbsp;&nbsp;" +
                   "<span class='glyphicon glyphicon-trash' title='{{_('Delete Link')}}' style='cursor: pointer;  font-size: 12px; color:#eee;' ></span>&nbsp;&nbsp;" +
                   "<span class='glyphicon glyphicon-repeat' title='{{_('Restart Link')}}' style='cursor: pointer; font-size: 12px; color:#eee;' ></span></div>");

        var $div = $("<div></div>");
        $div.attr("id","file_" + file.fid);
        $div.css("padding-left", "30px");
        $div.css("cursor", "grab");
        $div.addClass("child");
        $div.html($html);

        $li.data("lid", file.fid);
        $li.append($div);
        $ul.append($li);

        thisObject.registerLinkEvents();

        thisObject.get_pyload().register_listener(thisObject.event_handler);
    };

    this.registerLinkEvents = function ()
    {
        $ul.children("li").each(function(child)
        {
            var lid, lid_match = $(this).find('.child').attr('id').match(/[0-9]+/);
            if (lid_match)
            {
                lid = lid_match[0];
            }
            var imgs = $(this).find('.child_secrow span');
            $(imgs[3]).bind('click',{ lid: lid}, function(e) {
                $.get("/api/delete_files", {"fids": [lid]}, function () {
                    $('#file_' + lid).remove()
                }).fail(function () {
                    indicateFail();
                });
            });

            $(imgs[4]).bind('click',{ lid: lid},function(e) {
                $.get("/api/restart_file", {"lid": lid}, function () {
                    var ele1 = $('#file_' + lid);
                    var imgs1 = $(ele1).find(".glyphicon");
                    $(imgs1[0]).attr( "class","glyphicon glyphicon-time text-info");
                    var spans = $(ele1).find(".child_status");
                    $(spans[1]).html("{{_('queued')}}");
                    indicateSuccess();
                }).fail(function () {
                    indicateFail();
                });
            });
        });


        $ul.sortable({
            handle: ".child",
            axis: "y",
            cursor: "grabbing",
            start: function(e, ui) {
                $(this).attr('data-previndex', ui.item.index());
            },
            stop: function(event, ui) {
                var new_index = ui.item.index();
                var old_index = $(this).attr('data-previndex');
                $(this).removeAttr('data-previndex');
                if (new_index === old_index) {
                    return false;
                }
                indicateLoad();
                $.get("/json/link_order", {"lid": ui.item.data('lid'), "new_index": new_index}, function () {
                    indicateFinish();
                    return true;
                } ).fail(function () {
                    indicateFail();
                    return false;
                });
          }
        });
    };

    this.get_pyload = function()
    {
        return package.get_pyload();
    };

    this.humanFileSize = function(filesize)
    {
        return package.humanFileSize(filesize);
    }

    initialize()
}

function Package(ui, id, ele)
{
    // private variables
    var linksLoaded = false;
    var thisObject;
    var buttons;
    var name;
    var password;
    var folder;

    this.initialize = function ()
    {
        thisObject = this;
        if (!ele) {
            this.createElement();
        } else {
            jQuery.data(ele,"pid", id);
            this.parseElement();
        }

        var pname = $(ele).find('.packagename');

        buttons = $(ele).find('.buttons');
        buttons.css("opacity", 0);

        $(pname).mouseenter(function(e) {
            $(this).find('.buttons').fadeTo('fast', 1)
        });

        $(pname).mouseleave( function(e) {
            $(this).find('.buttons').fadeTo('fast', 0)
        });

        thisObject.get_pyload().register_listener(thisObject.event_handler);
    };

    this.event_handler = function(event)
    {
        data = JSON.parse(event.data);
        if (data.message == 'update_queue_pack' && data.payload.id == id)
        {
            ele.find('.progress-bar').css('width', data.payload.progress+'%');
            ele.find('.progress-bar-file-label').text(data.payload.finished_files+' / '+data.payload.total_files);
            ele.find('.progress-bar-size-label').text(self.humanFileSize(data.payload.downloaded_size)+' / '+self.humanFileSize(data.payload.total_size));
        }
    }

    this.createElement = function () {
        alert("create");
    };

    this.parseElement = function ()
    {
        var imgs = $(ele).find('span');

        name = $(ele).find('.name');
        folder =  $(ele).find('.folder');
        password = $(ele).find('.password');

        $(imgs[3]).click(this.deletePackage);
        $(imgs[4]).click(this.restartPackage);
        $(imgs[5]).click(this.editPackage);
        $(imgs[6]).click(this.movePackage);
        $(imgs[7]).click(this.editOrder);

        $(ele).find('.packagename').click(this.toggle);
    };

    this.loadLinks = function () {
        indicateLoad();
        $.get("/json/package", {"id": id}, thisObject.createLinks)
        .fail(function () {
            indicateFail();
            return false;
        })
        .done(function() {
            return true;
        });
    };

    this.createLinks = function(data)
    {
        var ul = $("#sort_children_" + id);
        ul.html("");
        $.each(data.links, function(key, link) {
            new File(thisObject, link)
        });

        linksLoaded = true;
        indicateFinish();
        thisObject.toggle();
    };

    this.toggle = function () {
        var icon = $(ele).find('.packageicon');
        var child = $(ele).find('.children');
        if (child.css('display') === "block") {
            $(child).fadeOut();
            icon.removeClass('glyphicon-folder-open');
            icon.addClass('glyphicon-folder-close');
        } else {
            if (!linksLoaded) {
                if (!thisObject.loadLinks()) {
                    return;
                }
            } else {
                $(child).fadeIn();
            }
            icon.removeClass('glyphicon-folder-close');
            icon.addClass('glyphicon-folder-open');
        }
    };

    this.deletePackage = function(event) {
        indicateLoad();
        $.get("/api/delete_packages", {"ids": [id]}, function () {
            $(ele).remove();
            indicateFinish();
        }).fail(function () {
            indicateFail();
        });

        event.stopPropagation();
        event.preventDefault();
    };

    this.restartPackage = function(event) {
        indicateLoad();
        $.get("/api/restart_package", {"id": id}, function () {
            thisObject.close();
            indicateSuccess();
        }).fail(function () {
            indicateFail();
        });
        event.stopPropagation();
        event.preventDefault();
    };

    this.close = function () {
        var child = $(ele).find('.children');
        if (child.css('display') === "block") {
            $(child).fadeOut();
            var icon = $(ele).find('.packageicon');
            icon.removeClass('glyphicon-folder-open');
            icon.addClass('glyphicon-folder-close');
        }
        var ul = $("#sort_children_" + id);
        $(ul).html("");
        linksLoaded = false;
    };

    this.movePackage = function(event) {
        indicateLoad();
        $.get("/json/move_package", {"target": ((ui.type + 1) % 2), "id": id}, function () {
            $(ele).remove();
            indicateFinish();
        }).fail(function () {
            indicateFail();
        });
        event.stopPropagation();
        event.preventDefault();
    };

    this.editOrder = function(event) {
        indicateLoad();
        $.get("/json/package", {"id": id}, function(data){
            length = data.links.length;
            for (i = 1; i <= length/2; i++){
                order = data.links[length-i].fid + '|' + (i-1);
                $.get("/json/link_order", {"order": order}).fail(function () {
                    indicateFail();
                });
            }
        });
        indicateFinish();
        thisObject.close();
        event.stopPropagation();
        event.preventDefault();
    };


    this.editPackage = function(event) {
        event.stopPropagation();
        event.preventDefault();
        $("#pack_form").off("submit").submit(thisObject.savePackage);

        $("#pack_id").val(id[0]);
        $("#pack_name").val(name.text());
        $("#pack_folder").val(folder.text());
        $("#pack_pws").val(password.text());
        $('#pack_box').modal('show');
    };

    this.savePackage = function(event) {
        $.ajax({
            url: "/json/edit_package",
            type: 'post',
            dataType: 'json',
            data: $('#pack_form').serialize()
        });
        event.preventDefault();
        name.text( $("#pack_name").val());
        folder.text( $("#pack_folder").val());
        password.text($("#pack_pws").val());
        $('#pack_box').modal('hide');
    };

    this.get_id = function()
    {
        return id;
    }

    this.get_pyload = function()
    {
        return ui.get_pyload()
    }

    this.humanFileSize = function(filesize)
    {
        return ui.humanFileSize(filesize);
    }

    this.initialize();
}

{% endautoescape %}
