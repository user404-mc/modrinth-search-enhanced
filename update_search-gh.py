import os

def generate_index_html():
    """Generate index.html with multi‑term AND search."""
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Modrinth Enhanced Search</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f0f0f0; }
        #search { width: 100%; padding: 10px; font-size: 16px; margin-bottom: 20px; }
        .project { background: white; margin-bottom: 10px; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .project.highlighted { border-left: 5px solid gold; }
        .project h3 { margin: 0 0 5px; }
        .project h3 a { color: #0366d6; text-decoration: none; }
        .project p { margin: 5px 0; color: #333; }
        .project .meta { font-size: 0.9em; color: #666; }
        .project .tags { display: inline-block; background: #e1e1e1; padding: 2px 6px; border-radius: 3px; margin: 2px; }
        .highlighted-badge { background: gold; padding: 2px 8px; border-radius: 10px; font-size: 0.8em; font-weight: bold; margin-left: 10px; }
        #status { text-align: center; color: #666; }
        .api-notice { margin-top: 20px; padding: 15px; background: #e8f0fe; border-radius: 5px; border: 1px solid #b0c4de; }
        .api-notice a { color: #0366d6; }
        #pagination { display: flex; justify-content: center; align-items: center; gap: 12px; margin-top: 20px; }
        #pagination button { padding: 5px 15px; cursor: pointer; }
        #pagination span { font-weight: bold; }
        #pagination button:disabled { opacity: 0.5; cursor: default; }
    </style>
</head>
<body>
    <h1>Modrinth Enhanced Search</h1>
    <input type="text" id="search" placeholder="Search mods, plugins, modpacks..." autofocus>
    <div id="results"></div>
    <div id="status">Loading data...</div>
    <div id="pagination" style="display:none;">
        <button id="prevPage" disabled>◀ Previous</button>
        <span id="pageInfo">Page 1 of 1</span>
        <button id="nextPage" disabled>Next ▶</button>
    </div>
    <div class="api-notice">
        <strong>API available:</strong> Use <a href="/modrinth-search-enhanced/api.html" target="_blank">/modrinth-search-enhanced/api.html</a> for documentation,
        or call <code>/modrinth-search-enhanced/api.js?q=...&callback=myFunc</code> (JSONP) directly.
    </div>
    <script>
        const DATA_PATH = 'data/';
        const PAGE_SIZE = 20;

        let projects = [];
        let highlighted = [];
        let tags = {};
        let filteredResults = [];
        let currentPage = 0;

        async function loadProjects() {
            const indexResp = await fetch(DATA_PATH + 'projects_index.json');
            if (!indexResp.ok) throw new Error('Failed to load projects_index.json');
            const index = await indexResp.json();

            if (index.type === 'single') {
                const resp = await fetch(DATA_PATH + index.file);
                if (!resp.ok) throw new Error('Failed to load ' + index.file);
                return await resp.json();
            } else if (index.type === 'chunks') {
                const chunkPromises = index.files.map(file =>
                    fetch(DATA_PATH + file).then(r => {
                        if (!r.ok) throw new Error('Failed to load ' + file);
                        return r.json();
                    })
                );
                const chunks = await Promise.all(chunkPromises);
                return chunks.flat();
            } else {
                throw new Error('Unknown index type: ' + index.type);
            }
        }

        async function loadData() {
            try {
                const [projData, highResp, tagsResp] = await Promise.all([
                    loadProjects(),
                    fetch(DATA_PATH + 'highlighted.json'),
                    fetch(DATA_PATH + 'tags.json')
                ]);
                if (!highResp.ok) throw new Error('Failed to load highlighted.json');
                if (!tagsResp.ok) throw new Error('Failed to load tags.json');
                projects = projData;
                highlighted = await highResp.json();
                tags = await tagsResp.json();
                document.getElementById('status').textContent = `Loaded ${projects.length} projects.`;
                doSearch('');
            } catch (e) {
                document.getElementById('status').textContent = 'Error loading data: ' + e.message;
                console.error(e);
            }
        }

        function doSearch(query) {
            query = query.trim();
            const terms = query ? query.toLowerCase().split(/\s+/) : [];
            const results = [];
            for (const proj of projects) {
                const catText = (proj.categories || []).join(' ');
                const gameText = (proj.game_versions || []).join(' ');
                const tagList = tags[proj.slug] || [];
                const tagText = tagList.join(' ');
                const text = (proj.title + ' ' + proj.description + ' ' + proj.body + ' ' + catText + ' ' + gameText + ' ' + tagText).toLowerCase();
                let match = true;
                if (terms.length > 0) {
                    for (const term of terms) {
                        if (!text.includes(term)) {
                            match = false;
                            break;
                        }
                    }
                }
                if (match) {
                    results.push(proj);
                }
            }
            results.sort((a, b) => {
                const aHigh = highlighted.includes(a.slug);
                const bHigh = highlighted.includes(b.slug);
                if (aHigh && !bHigh) return -1;
                if (!aHigh && bHigh) return 1;
                return (b.downloads || 0) - (a.downloads || 0);
            });
            filteredResults = results;
            currentPage = 0;
            renderPage();
        }

        function renderPage() {
            const container = document.getElementById('results');
            const total = filteredResults.length;
            const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
            if (currentPage >= totalPages) currentPage = totalPages - 1;
            if (currentPage < 0) currentPage = 0;

            const start = currentPage * PAGE_SIZE;
            const end = Math.min(start + PAGE_SIZE, total);
            const pageResults = filteredResults.slice(start, end);

            if (total === 0) {
                container.innerHTML = '<p>No results found.</p>';
                document.getElementById('pagination').style.display = 'none';
                return;
            }

            let html = '';
            for (const proj of pageResults) {
                const isHighlighted = highlighted.includes(proj.slug);
                const tagList = tags[proj.slug] || [];
                const catList = proj.categories || [];
                const gameVersions = proj.game_versions || [];
                html += `<div class="project ${isHighlighted ? 'highlighted' : ''}">`;
                html += `<h3><a href="https://user404-mc.github.io/modrinth-enhanced/#project/${proj.slug}" target="_blank">${proj.title}</a>`;
                if (isHighlighted) html += `<span class="highlighted-badge">★ Highlighted</span>`;
                html += `</h3>`;
                html += `<p>${proj.description || ''}</p>`;
                html += `<div class="meta">`;
                if (catList.length) html += `Categories: ${catList.map(c => `<span class="tags">${c}</span>`).join(' ')}; `;
                if (gameVersions.length) html += `Versions: ${gameVersions.join(', ')}; `;
                if (tagList.length) html += `Tags: ${tagList.map(t => `<span class="tags">${t}</span>`).join(' ')}; `;
                html += `Downloads: ${proj.downloads || 0}`;
                html += `</div>`;
                html += `</div>`;
            }
            container.innerHTML = html;

            const paginationDiv = document.getElementById('pagination');
            paginationDiv.style.display = 'flex';
            document.getElementById('pageInfo').textContent = `Page ${currentPage+1} of ${totalPages}`;
            document.getElementById('prevPage').disabled = (currentPage === 0);
            document.getElementById('nextPage').disabled = (currentPage >= totalPages - 1);
        }

        document.getElementById('search').addEventListener('input', function(e) {
            doSearch(this.value);
        });
        document.getElementById('prevPage').addEventListener('click', function() {
            if (currentPage > 0) { currentPage--; renderPage(); }
        });
        document.getElementById('nextPage').addEventListener('click', function() {
            const totalPages = Math.ceil(filteredResults.length / PAGE_SIZE);
            if (currentPage < totalPages - 1) { currentPage++; renderPage(); }
        });

        loadData();
    </script>
</body>
</html>
'''
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)


def generate_api_js():
    """Generate api.js with multi‑term AND search, highlighting and tags."""
    js = '''// Modrinth Enhanced Search API (JSONP) with multi‑term AND search, highlighting and tags
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
'''
    with open("api.js", "w", encoding="utf-8") as f:
        f.write(js)

def generate_api_html():
    apihtml = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Modrinth Enhanced Search API</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f0f0f0; }
        code { background: #eee; padding: 2px 5px; border-radius: 3px; }
        pre { background: #eee; padding: 10px; border-radius: 5px; overflow-x: auto; }
        .example { border: 1px solid #ccc; padding: 10px; margin: 10px 0; background: #fafafa; }
        .example button { margin-top: 5px; }
    </style>
</head>
<body>
    <h1>Modrinth Enhanced Search – API Documentation</h1>
    <p>This API loads the project index (possibly split into multiple files) and filters it.</p>

    <h2>Endpoint</h2>
    <p><code>/modrinth-search-enhanced/api.js</code></p>

    <h2>Parameters</h2>
    <ul>
        <li><strong>q</strong> – search string (matches title, description, body, categories, game versions)</li>
        <li><strong>category</strong> – exact category name (e.g., "technology", "magic")</li>
        <li><strong>client_side</strong> – "required", "optional", or "unsupported"</li>
        <li><strong>server_side</strong> – same as above</li>
        <li><strong>limit</strong> – number of results per page (default: 20)</li>
        <li><strong>offset</strong> – starting index (default: 0)</li>
        <li><strong>callback</strong> – the name of the JavaScript function to call with the result (JSONP)</li>
    </ul>

    <h2>Response format</h2>
    <pre>{
    total: number,
    limit: number,
    offset: number,
    results: [ ... ]
}</pre>

    <h2>Example usage</h2>
    <pre>&lt;script src="/modrinth-search-enhanced/api.js?q=mining&limit=5&offset=10&callback=showResults"&gt;&lt;/script&gt;
&lt;script&gt;
function showResults(data) {
    console.log(data.total, data.results);
}
&lt;/script&gt;</pre>

    <h2>Live test</h2>
    <div class="example">
        <label>Search: <input type="text" id="testQuery" value="fabric" /></label>
        <label>Limit: <input type="number" id="testLimit" value="5" /></label>
        <label>Offset: <input type="number" id="testOffset" value="0" /></label>
        <button onclick="testAPI()">Run</button>
        <pre id="testOutput">Results will appear here...</pre>
    </div>

    <h2>Additional REST‑like endpoints</h2>
    <p>You can also fetch individual project details via:</p>
    <p><code>/modrinth-search-enhanced/api/projects/&lt;slug&gt;.json</code></p>
    <p>Example: <a href="/modrinth-search-enhanced/api/projects/sodium.json" target="_blank">/modrinth-search-enhanced/api/projects/sodium.json</a></p>

    <script>
        function testAPI() {
            var q = document.getElementById('testQuery').value.trim();
            var limit = parseInt(document.getElementById('testLimit').value) || 5;
            var offset = parseInt(document.getElementById('testOffset').value) || 0;
            var output = document.getElementById('testOutput');
            output.textContent = 'Loading...';
            var script = document.createElement('script');
            script.src = '/modrinth-search-enhanced/api.js?q=' + encodeURIComponent(q) + '&limit=' + limit + '&offset=' + offset + '&callback=showTestResults';
            document.body.appendChild(script);
            window.showTestResults = function(data) {
                output.textContent = JSON.stringify(data, null, 2);
                delete window.showTestResults;
                document.body.removeChild(script);
            };
        }
    </script>
</body>
</html>
'''
    with open("api.html", "w", encoding="utf-8") as f:
        f.write(apihtml)


if __name__ == "__main__":
    generate_index_html()
    generate_api_js()
    generate_api_html()
    print("Updated search logic in index.html and api.js (with highlighting and tags)")
