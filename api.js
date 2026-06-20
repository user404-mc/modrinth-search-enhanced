// Modrinth Enhanced Search API (JSONP) with multi‑term AND search, highlighting and tags
(function() {
    var currentScript = document.currentScript || document.scripts[document.scripts.length - 1];
    var src = currentScript.src;
    var query = src.split('?')[1] || '';
    var params = new URLSearchParams(query);
    var callback = params.get('callback') || 'console.log';
    var q = (params.get('q') || '').trim();
    var category = (params.get('category') || '').toLowerCase().trim();
    var clientSide = (params.get('client_side') || '').toLowerCase().trim();
    var serverSide = (params.get('server_side') || '').toLowerCase().trim();
    var limit = parseInt(params.get('limit')) || 20;
    var offset = parseInt(params.get('offset')) || 0;

    async function loadProjects() {
        var indexResp = await fetch('/modrinth-search-enhanced/data/projects_index.json');
        if (!indexResp.ok) throw new Error('Failed to load projects_index.json');
        var index = await indexResp.json();

        if (index.type === 'single') {
            var resp = await fetch('/modrinth-search-enhanced/data/' + index.file);
            if (!resp.ok) throw new Error('Failed to load ' + index.file);
            return await resp.json();
        } else if (index.type === 'chunks') {
            var chunkPromises = index.files.map(function(file) {
                return fetch('/modrinth-search-enhanced/data/' + file).then(function(r) {
                    if (!r.ok) throw new Error('Failed to load ' + file);
                    return r.json();
                });
            });
            var chunks = await Promise.all(chunkPromises);
            return chunks.reduce(function(acc, chunk) { return acc.concat(chunk); }, []);
        } else {
            throw new Error('Unknown index type: ' + index.type);
        }
    }

    async function loadHighlighted() {
        var resp = await fetch('/modrinth-search-enhanced/data/highlighted.json');
        if (!resp.ok) return []; // fallback
        return await resp.json();
    }

    async function loadTags() {
        var resp = await fetch('/modrinth-search-enhanced/data/tags.json');
        if (!resp.ok) return {};
        return await resp.json();
    }

    (async function() {
        try {
            var [projects, highlighted, tags] = await Promise.all([
                loadProjects(),
                loadHighlighted(),
                loadTags()
            ]);
            var terms = q ? q.toLowerCase().split(/\s+/) : [];
            var results = [];
            for (var i = 0; i < projects.length; i++) {
                var p = projects[i];
                var tagList = tags[p.slug] || [];
                var tagText = tagList.join(' ');
                var text = (p.title + ' ' + p.description + ' ' + p.body + ' ' + (p.categories || []).join(' ') + ' ' + (p.game_versions || []).join(' ') + ' ' + tagText).toLowerCase();
                var match = true;
                if (terms.length > 0) {
                    for (var t = 0; t < terms.length; t++) {
                        if (!text.includes(terms[t])) {
                            match = false;
                            break;
                        }
                    }
                }
                if (match && category && !(p.categories || []).some(function(c) { return c.toLowerCase() === category; })) match = false;
                if (match && clientSide && p.client_side !== clientSide) match = false;
                if (match && serverSide && p.server_side !== serverSide) match = false;
                if (match) results.push(p);
            }
            // Sort: highlighted first, then by downloads
            results.sort(function(a, b) {
                var aHigh = highlighted.includes(a.slug);
                var bHigh = highlighted.includes(b.slug);
                if (aHigh && !bHigh) return -1;
                if (!aHigh && bHigh) return 1;
                return (b.downloads || 0) - (a.downloads || 0);
            });
            var total = results.length;
            var paginated = results.slice(offset, offset + limit);
            var response = { total: total, limit: limit, offset: offset, results: paginated };
            var func = window[callback];
            if (typeof func === 'function') {
                func(response);
            } else {
                console.warn('Callback function "' + callback + '" not found. Use JSONP style.');
                console.log(response);
            }
        } catch (err) {
            console.error('API error:', err);
            var func = window[callback];
            if (typeof func === 'function') {
                func({ error: err.message });
            }
        }
    })();
})();
