#target photoshop
(function () {
    function parseJob(source) {
        if (typeof JSON !== "undefined" && typeof JSON.parse === "function") {
            return JSON.parse(source);
        }
        var safe = /^[\],:{}\s]*$/.test(source
            .replace(/\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g, "@")
            .replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g, "]")
            .replace(/(?:^|:|,)(?:\s*\[)+/g, ""));
        if (!safe) { throw new Error("Invalid JSON input"); }
        return eval("(" + source + ")");
    }

    function fileFromProject(projectFolder, path) {
        if (!path) { return null; }
        var normalized = String(path).replace(/\\/g, "/");
        if (/^(?:[A-Za-z]:\/|\/)/.test(normalized)) { return new File(normalized); }
        return new File(projectFolder.fsName + "/" + normalized);
    }

    function readJson(file) {
        file.encoding = "UTF8";
        if (!file.open("r")) { throw new Error("Cannot read " + file.fsName); }
        var contents = file.read();
        file.close();
        return parseJob(contents);
    }

    function findGroupDeep(container, name) {
        for (var i = 0; i < container.layerSets.length; i++) {
            var group = container.layerSets[i];
            if (group.name === name) { return group; }
            var found = findGroupDeep(group, name);
            if (found !== null) { return found; }
        }
        return null;
    }

    function childGroup(container, name) {
        for (var i = 0; i < container.layerSets.length; i++) {
            if (container.layerSets[i].name === name) { return container.layerSets[i]; }
        }
        throw new Error("Missing group '" + name + "' inside '" + container.name + "'");
    }

    function artLayer(container, name) {
        for (var i = 0; i < container.artLayers.length; i++) {
            if (container.artLayers[i].name === name) { return container.artLayers[i]; }
        }
        throw new Error("Missing layer '" + name + "' inside '" + container.name + "'");
    }

    function textLayers(container) {
        var result = [];
        for (var i = 0; i < container.artLayers.length; i++) {
            var layer = container.artLayers[i];
            if (layer.kind === LayerKind.TEXT) { result.push(layer); }
        }
        return result;
    }

    function textLayerByNameDeep(container, name) {
        for (var i = 0; i < container.artLayers.length; i++) {
            var layer = container.artLayers[i];
            if (layer.name === name && layer.kind === LayerKind.TEXT) { return layer; }
        }
        for (var j = 0; j < container.layerSets.length; j++) {
            var found = textLayerByNameDeep(container.layerSets[j], name);
            if (found !== null) { return found; }
        }
        return null;
    }

    function setText(layer, value) {
        if (layer.kind !== LayerKind.TEXT) { throw new Error("Not a text layer: " + layer.name); }
        layer.textItem.contents = String(value);
        layer.visible = true;
    }

    function setMvpStats(card, player) {
        var nickGroup = childGroup(card, "Никнейм");
        var nickTexts = textLayers(nickGroup);
        if (nickTexts.length !== 1) { throw new Error("Expected 1 nickname layer in " + card.name); }
        setText(nickTexts[0], player.name);

        var statsGroup = childGroup(card, "Статы на белом фоне");
        var numericTexts = textLayers(statsGroup);
        if (numericTexts.length !== 2) { throw new Error("Expected 2 stat layers in " + card.name); }
        numericTexts.sort(function (a, b) {
            return a.bounds[0].as("px") - b.bounds[0].as("px");
        });
        setText(numericTexts[0], player.kills);
        setText(numericTexts[1], formatThousands(player.damage));
    }

    function formatThousands(value) {
        var str = String(value), result = "";
        while (str.length > 3) {
            result = "," + str.substr(str.length - 3) + result;
            str = str.substr(0, str.length - 3);
        }
        return str + result;
    }

    var LEGENDS = {
        "alter":"Альтер", "ash":"Эш", "bangalore":"Бангалор",
        "ballistic":"Баллистик", "bloodhound":"Бладхаунд",
        "catalyst":"Каталист", "caustic":"Каустик", "conduit":"Кондуит",
        "crypto":"Крипто", "fuse":"Фьюз", "gibraltar":"Гиббон",
        "horizon":"Хорайзон", "lifeline":"Лайфлайн", "loba":"Лоба",
        "madmaggie":"Мэгги", "mirage":"Мираж", "newcastle":"Ньюкасл",
        "octane":"Октейн", "pathfinder":"Пат", "rampart":"Рампарт",
        "revenant":"Ревенант", "seer":"Сиар", "sparrow":"Спарроу",
        "valkyrie":"Валькирия", "vantage":"Вантага",
        "wattson":"Ваттсон", "wraith":"Рэйф"
    };
    var LEGEND_LAYER_NAMES = {};
    for (var slug in LEGENDS) {
        if (LEGENDS.hasOwnProperty(slug)) { LEGEND_LAYER_NAMES[LEGENDS[slug]] = true; }
    }

    function selectLegend(card, legend, warnings) {
        var artGroup = childGroup(card, "Персонажи");
        var desired = LEGENDS[String(legend).toLowerCase()];
        var found = false;
        for (var i = 0; i < artGroup.artLayers.length; i++) {
            var layer = artGroup.artLayers[i];
            if (LEGEND_LAYER_NAMES[layer.name]) {
                layer.visible = (layer.name === desired);
                if (layer.visible) { found = true; }
            }
        }
        if (!found) { warnings.push("No formatted legend layer for: " + legend); }
    }

    function hideOriginalTeamLogo(card) {
        var group = childGroup(card, "Лого команды");
        for (var i = 0; i < group.artLayers.length; i++) {
            var layer = group.artLayers[i];
            if (layer.name !== "Прямоугольник 3") { layer.visible = false; }
        }
    }

    function replaceSmartContents(doc, smartLayer, filename, warnings) {
        if (!filename) {
            smartLayer.visible = false;
            warnings.push("No preformatted CIS MVP portrait; output is a draft.");
            return;
        }
        var photo = new File(filename);
        if (!photo.exists) {
            smartLayer.visible = false;
            warnings.push("Photo missing: " + filename);
            return;
        }
        try {
            if (smartLayer.kind !== LayerKind.SMARTOBJECT) {
                throw new Error("Target is not a smart object");
            }
            app.activeDocument = doc;
            doc.activeLayer = smartLayer;
            var command = stringIDToTypeID("placedLayerReplaceContents");
            var desc = new ActionDescriptor();
            desc.putPath(charIDToTypeID("null"), photo);
            executeAction(command, desc, DialogModes.NO);
            smartLayer.visible = true;
        } catch (err) {
            smartLayer.visible = false;
            warnings.push("Photo replacement failed: " + err);
        }
    }

    function fillMvp(doc, job, warnings, projectFolder) {
        var heading = textLayerByNameDeep(doc, "MATCH 5");
        var subtitle = textLayerByNameDeep(doc, "ALGS CHAMPIONSHIP 2025 - MATCH 1");
        if (!heading || !subtitle) {
            throw new Error("MVP heading text layers not found. Use the original supplied PSD.");
        }
        setText(heading, "MATCH " + job.match_number);
        setText(subtitle, job.event_name + " - MATCH " + job.match_number);
        if (job.players.length !== 3) { throw new Error("Expected exactly 3 MVP players"); }
        for (var i = 0; i < 3; i++) {
            var card = findGroupDeep(doc, "Статы " + (i + 1) + " игрока");
            if (!card) { throw new Error("Missing card group for player " + (i + 1)); }
            setMvpStats(card, job.players[i]);
            selectLegend(card, job.players[i].legend, warnings);
            hideOriginalTeamLogo(card);
        }
        var photoLayer = findArtLayerDeep(doc, "Фото (два клика)");
        if (!photoLayer) { throw new Error("MVP photo smart object not found"); }
        var photoFile = fileFromProject(projectFolder, job.mvp_photo);
        replaceSmartContents(doc, photoLayer, photoFile ? photoFile.fsName : null, warnings);
    }

    function findArtLayerDeep(container, name) {
        for (var i = 0; i < container.artLayers.length; i++) {
            if (container.artLayers[i].name === name) { return container.artLayers[i]; }
        }
        for (var j = 0; j < container.layerSets.length; j++) {
            var found = findArtLayerDeep(container.layerSets[j], name);
            if (found !== null) { return found; }
        }
        return null;
    }

    function fillTable(doc, job) {
        if (job.rows.length > 20) { throw new Error("The table template supports 20 rows"); }
        for (var i = 0; i < job.rows.length; i++) {
            var rank = job.rows[i];
            var group = findGroupDeep(doc, String(i + 1));
            if (!group) { throw new Error("Missing rank group: " + (i + 1)); }
            setText(artLayer(group, "team name"), rank.team);
            var killsGroup = childGroup(group, "киллы");
            var pointsGroup = childGroup(group, "тотал скор");
            var killsTexts = textLayers(killsGroup);
            var pointsTexts = textLayers(pointsGroup);
            if (killsTexts.length !== 1 || pointsTexts.length !== 1) {
                throw new Error("Scoreboard cells are not text layers in rank " + (i + 1));
            }
            setText(killsTexts[0], rank.kills);
            setText(pointsTexts[0], rank.points);
        }
        var header = textLayerByNameDeep(doc, "ALGS CHAMPIONSHIP 2025");
        if (header && job.event_name) { setText(header, job.event_name); }
    }

    function createFolderIfMissing(file) {
        var parent = file.parent;
        if (!parent.exists && !parent.create()) {
            throw new Error("Cannot create output folder " + parent.fsName);
        }
    }

    function savePSDandPNG(doc, job, projectFolder) {
        var psd = fileFromProject(projectFolder, job.output_psd);
        var png = fileFromProject(projectFolder, job.output_png);
        createFolderIfMissing(psd);
        createFolderIfMissing(png);
        var psdOptions = new PhotoshopSaveOptions();
        psdOptions.layers = true;
        psdOptions.embedColorProfile = true;
        doc.saveAs(psd, psdOptions, true, Extension.LOWERCASE);
        var pngOptions = new PNGSaveOptions();
        pngOptions.interlaced = false;
        doc.saveAs(png, pngOptions, true, Extension.LOWERCASE);
    }

    var oldDialogs = app.displayDialogs;
    var doc = null;
    var warnings = [];
    try {
        var file = File.openDialog("Choose JSON exported by main.py", "JSON files:*.json");
        if (file === null) { return; }
        var job = readJson(file);
        if (job.type !== "table" && job.type !== "match_mvp") {
            throw new Error("Unknown job type: " + job.type);
        }
        var projectFolder = file.parent.parent.parent;
        var source = fileFromProject(projectFolder, job.template_psd);
        if (!source.exists) { throw new Error("Original PSD not found: " + source.fsName); }
        doc = app.open(source);
        app.displayDialogs = DialogModes.NO;
        if (job.type === "table") { fillTable(doc, job); }
        else { fillMvp(doc, job, warnings, projectFolder); }
        savePSDandPNG(doc, job, projectFolder);
        var message = "Saved layered PSD:\n" + fileFromProject(projectFolder, job.output_psd).fsName + "\n\nPNG:\n" + fileFromProject(projectFolder, job.output_png).fsName;
        if (warnings.length) { message += "\n\nWARNINGS:\n" + warnings.join("\n"); }
        alert(message);
    } catch (err) {
        alert("Photoshop export failed:\n" + err);
    } finally {
        app.displayDialogs = oldDialogs;
        if (doc !== null) {
            try { doc.close(SaveOptions.DONOTSAVECHANGES); } catch (ignore) {}
        }
    }
})();
