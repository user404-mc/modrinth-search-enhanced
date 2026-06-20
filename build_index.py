import requests
import json
import time
import os
import math
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://api.modrinth.com/v2"
DATA_DIR = "data-test2"
API_DIR = "api-2"
PROJECTS_API_DIR = os.path.join(API_DIR, "projects")

MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024

USER_AGENT = "Mozilla/5.0 (compatible; ModrinthSearchEnhanced/1.0; +https://github.com/user404-mc)"
HEADERS = {"User-Agent": USER_AGENT}

# Session with retry strategy
session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)


def fetch_all_projects():
    """Fetch all projects using the search endpoint with automatic retries."""
    projects = []
    offset = 0
    limit = 100
    while True:
        url = f"{BASE_URL}/search?limit={limit}&offset={offset}"
        try:
            resp = session.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching search results after retries: {e}")
            break
        data = resp.json()
        hits = data.get("hits", [])
        if not hits:
            break
        projects.extend(hits)
        offset += limit
        if offset >= data.get("total_hits", 0):
            break
        time.sleep(0.2)
    return projects


def fetch_project_details(slug):
    """Fetch project details with retry support."""
    url = f"{BASE_URL}/project/{slug}"
    try:
        resp = session.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {slug} after retries: {e}")
        return None
    return resp.json()


def build_project_data(hit, details):
    """Combine search hit and project details into a single object."""
    return {
        "id": hit.get("project_id"),
        "slug": hit.get("slug"),
        "title": hit.get("title"),
        "description": hit.get("description"),
        "body": details.get("body", ""),
        "categories": hit.get("categories", []),
        "client_side": hit.get("client_side"),
        "server_side": hit.get("server_side"),
        "downloads": hit.get("downloads", 0),
        "followers": hit.get("followers", 0),
        "game_versions": details.get("game_versions", []),
        "date_updated": hit.get("date_updated")
    }


def generate_index_html():
    """Generate the main search page with pagination and chunk loading."""
    # (same as in recovery script – copy from above or keep as is)
    # I'll include it here shortened for brevity, but you should copy the full function from recovery.
    # For completeness, I'll paste it again.
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
        <strong>API available:</strong> Use <a href="/api.html" target="_blank">/api.html</a> for documentation,
        or call <code>/api.js?q=...&callback=myFunc</code> (JSONP) directly.
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
            const terms = query ? query.toLowerCase().split(/\\s+/) : [];
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
</html>'''
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)


def generate_api_js():
    """Generate the JSONP API with chunk support and pagination."""
    # (same as in recovery script – copy from above)
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
        var indexResp = await fetch('/data/projects_index.json');
        if (!indexResp.ok) throw new Error('Failed to load projects_index.json');
        var index = await indexResp.json();

        if (index.type === 'single') {
            var resp = await fetch('/data/' + index.file);
            if (!resp.ok) throw new Error('Failed to load ' + index.file);
            return await resp.json();
        } else if (index.type === 'chunks') {
            var chunkPromises = index.files.map(function(file) {
                return fetch('/data/' + file).then(function(r) {
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
        var resp = await fetch('/data/highlighted.json');
        if (!resp.ok) return []; // fallback
        return await resp.json();
    }

    async function loadTags() {
        var resp = await fetch('/data/tags.json');
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
            var terms = q ? q.toLowerCase().split(/\\s+/) : [];
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


def generate_api_docs():
    """Generate the API documentation page."""
    # (same as in recovery script)
    html = '''<!DOCTYPE html>
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
    <p><code>/api.js</code></p>

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
    <pre>&lt;script src="/api.js?q=mining&limit=5&offset=10&callback=showResults"&gt;&lt;/script&gt;
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
    <p><code>/api/projects/&lt;slug&gt;.json</code></p>
    <p>Example: <a href="/api/projects/sodium.json" target="_blank">/api/projects/sodium.json</a></p>

    <script>
        function testAPI() {
            var q = document.getElementById('testQuery').value.trim();
            var limit = parseInt(document.getElementById('testLimit').value) || 5;
            var offset = parseInt(document.getElementById('testOffset').value) || 0;
            var output = document.getElementById('testOutput');
            output.textContent = 'Loading...';
            var script = document.createElement('script');
            script.src = '/api.js?q=' + encodeURIComponent(q) + '&limit=' + limit + '&offset=' + offset + '&callback=showTestResults';
            document.body.appendChild(script);
            window.showTestResults = function(data) {
                output.textContent = JSON.stringify(data, null, 2);
                delete window.showTestResults;
                document.body.removeChild(script);
            };
        }
    </script>
</body>
</html>'''
    with open("api.html", "w", encoding="utf-8") as f:
        f.write(html)


def generate_individual_project_files(projects):
    """Generate one JSON file per project in api/projects/."""
    os.makedirs(PROJECTS_API_DIR, exist_ok=True)
    for proj in projects:
        slug = proj.get("slug")
        if not slug:
            continue
        path = os.path.join(PROJECTS_API_DIR, f"{slug}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(proj, f, ensure_ascii=False, indent=2)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(API_DIR, exist_ok=True)

    print("Fetching all projects from search...")
    hits = fetch_all_projects()
    if not hits:
        print("No projects fetched. Exiting.")
        return
    print(f"Found {len(hits)} projects.")

    projects_data = []
    for i, hit in enumerate(hits):
        slug = hit.get("slug")
        print(f"Fetching details for {slug} ({i+1}/{len(hits)})")
        details = fetch_project_details(slug)
        if details:
            projects_data.append(build_project_data(hit, details))
        time.sleep(0.2)

    # Serialize and split if needed
    json_str = json.dumps(projects_data, ensure_ascii=False, indent=2)
    encoded = json_str.encode('utf-8')
    size_mb = len(encoded) / (1024 * 1024)
    print(f"Serialized project data size: {size_mb:.2f} MB")

    if len(encoded) > MAX_FILE_SIZE_BYTES:
        print(f"Size exceeds {MAX_FILE_SIZE_BYTES/(1024*1024):.0f} MB – splitting into chunks.")
        chunks = math.ceil(len(encoded) / (MAX_FILE_SIZE_BYTES * 0.9))
        chunk_size = math.ceil(len(projects_data) / chunks)
        files = []
        for i in range(chunks):
            start = i * chunk_size
            end = min((i + 1) * chunk_size, len(projects_data))
            chunk = projects_data[start:end]
            filename = f"projects_{i}.json"
            with open(os.path.join(DATA_DIR, filename), "w", encoding="utf-8") as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)
            files.append(filename)
            print(f"  Saved chunk {i+1}/{chunks} ({len(chunk)} projects) to {filename}")
        index = {"type": "chunks", "chunks": chunks, "files": files}
        with open(os.path.join(DATA_DIR, "projects_index.json"), "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)
        print(f"  Wrote index with {chunks} chunks.")
    else:
        with open(os.path.join(DATA_DIR, "projects.json"), "w", encoding="utf-8") as f:
            json.dump(projects_data, f, ensure_ascii=False, indent=2)
        index = {"type": "single", "file": "projects.json"}
        with open(os.path.join(DATA_DIR, "projects_index.json"), "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)
        print("  Saved single projects.json.")

    # Placeholder files
    highlight_path = os.path.join(DATA_DIR, "highlighted.json")
    if not os.path.exists(highlight_path):
        with open(highlight_path, "w") as f:
            json.dump([], f)

    tags_path = os.path.join(DATA_DIR, "tags.json")
    if not os.path.exists(tags_path):
        with open(tags_path, "w") as f:
            json.dump({}, f)

    # Generate individual project JSONs
    generate_individual_project_files(projects_data)

    # Generate the JSONP API, documentation, and main page
    generate_api_js()
    generate_api_docs()
    generate_index_html()

    print("Done! The output is in './' – ready for GitHub Pages.")
    print(f" - Main page: index.html (pagination + chunk loading)")
    print(f" - JSONP API: api.js (supports limit & offset)")
    print(f" - API docs: api.html")
    print(f" - Project details: {PROJECTS_API_DIR}/")


if __name__ == "__main__":
    main()
