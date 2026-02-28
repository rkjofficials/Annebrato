#!/usr/bin/env python3
"""
Enhanced HTTP server with searchable, categorized troubleshooting guide
- Simplified section layout (no cards)
- AJAX-based filtering and search
- Mobile-friendly responsive design
"""
from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
import html
import re
import urllib.parse
import json

PORT = 8000
TEXT_FILE = "steps.txt"

# cache parsed sections to avoid re-reading file on every request
SECTION_CACHE = None
CACHE_MTIME = 0

class TroubleshootHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        # API endpoint for search
        if path == "/api/search":
            self.handle_search_api(query_params)
            return
        
        # Editor interface
        if path == "/editor":
            self.send_editor_page()
            return
        
        # Main page
        if path in ("/", "/index.html"):
            self.send_main_page(query_params)
            return
        
        # CSS
        if path == '/style.css':
            self.send_css()
            return
        
        # Default
        super().do_GET()

    def load_sections(self):
        """Read and parse TEXT_FILE, caching the result until the file changes."""
        global SECTION_CACHE, CACHE_MTIME
        try:
            mtime = os.path.getmtime(TEXT_FILE)
        except OSError:
            return []

        if SECTION_CACHE is None or mtime != CACHE_MTIME:
            SECTION_CACHE = []
            CACHE_MTIME = mtime
            with open(TEXT_FILE, "r", encoding="utf-8") as f:
                raw = f.read()
            parts = re.split(r'(?m)^# (.+)$', raw)
            if parts[0].strip():
                SECTION_CACHE.append(("General", parts[0]))
            for i in range(1, len(parts), 2):
                name = parts[i].strip() if i < len(parts) else ""
                body = parts[i+1] if i+1 < len(parts) else ""
                if name:
                    SECTION_CACHE.append((name, body))
        return SECTION_CACHE

    def handle_search_api(self, query_params):
        """API endpoint for AJAX search returning snippets."""
        search_term = query_params.get('q', [''])[0].lower().strip()
        sections = self.load_sections()
        results = []

        for idx, (app_name, content) in enumerate(sections):
            if search_term and search_term not in content.lower():
                continue

            # snippet: first matching line plus maybe context
            snippet = ""
            if search_term:
                for line in content.split('\n'):
                    if search_term in line.lower():
                        snippet = line.strip()
                        # add simple highlight for API consumers
                        try:
                            regex = re.compile(re.escape(search_term), re.IGNORECASE)
                            snippet = regex.sub(r'<mark>\g<0></mark>', snippet)
                        except re.error:
                            pass
                        break
            
            # Create summary (first few non-heading lines)
            lines = content.split('\n')
            summary_lines = [l.strip() for l in lines[:5] if l.strip() and not l.startswith('#')]
            summary = ' '.join(summary_lines)[:100]

            # Count errors
            error_count = len(re.findall(r'- \*\*Error\*\*:|^- \*\*', content, re.MULTILINE))

            results.append({
                'app': app_name,
                'slug': f'app{idx}',
                'summary': summary,
                'snippet': snippet,
                'errors': error_count,
                'matched': bool(search_term)
            })

        self.send_json_response({"results": results, "count": len(results), "query": search_term})

    def send_json_response(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_editor_page(self):
        """Send the editor interface"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        # build editor HTML using plain string to simplify curly-brace handling
        editor_page = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Troubleshooting Editor</title>
<link rel="stylesheet" href="/style.css">
<style>
.editor-container { max-width: 900px; margin: 0 auto; padding: 1em; }
.editor-form { background: white; padding: 1.5em; border-radius: 8px; margin-bottom: 2em; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.form-group { margin: 1.2em 0; }
label { display: block; font-weight: 600; margin-bottom: 0.5em; color: #333; }
input[type="text"], textarea, select { 
    width: 100%; padding: 0.75em; border: 1px solid #ddd; 
    border-radius: 4px; font-family: monospace; font-size: 1em;
    box-sizing: border-box;
}
input:focus, textarea:focus { outline: none; border-color: #0066cc; box-shadow: 0 0 0 3px rgba(0,102,204,0.1); }
textarea { min-height: 200px; white-space: pre; }
button { 
    background: #0066cc; color: white; padding: 0.8em 1.5em; 
    border: none; border-radius: 4px; cursor: pointer; font-size: 1em; font-weight: 600;
}
button:hover { background: #0052a3; }
button:active { transform: scale(0.98); }
.editor-section h2 { color: #333; margin-top: 2em; margin-bottom: 1em; }
</style>
</head>
<body>
<div class="editor-container">
    <header class="header">
        <h1>📝 Troubleshooting Editor</h1>
    </header>
    
    <p><a href="/">← Back to troubleshooting guide</a></p>
    
    <div class="editor-form">
        <h2>Add New Application Section</h2>
        <form method="post" action="/editor">
            <div class="form-group">
                <label for="appName">Application Name:</label>
                <input type="text" id="appName" name="appName" placeholder="e.g. HP Printer Errors" required>
            </div>
            
            <div class="form-group">
                <label for="appSteps">Content:</label>
                <textarea id="appSteps" name="appSteps" placeholder="## Category Name&#10;- **Error Code**: Description and solution" required></textarea>
            </div>
            
            <button type="submit">Add Application</button>
        </form>
    </div>
    
    <div class="editor-section">
        <h2>Edit Full Content</h2>
        <form method="post" action="/editor">
            <div class="form-group">
                <textarea id="fullContent" name="fullContent"></textarea>
            </div>
            <button type="submit" name="action" value="save_full">Save Full Content</button>
        </form>
    </div>
</div>

<script>
fetch('{TEXT_FILE}')
    .then(r => r.text())
    .then(text => {
        document.getElementById('fullContent').value = text;
    })
    .catch(err => console.log('Could not load file'));
</script>
</body>
</html>"""
        # substitute placeholder for actual path
        editor_page = editor_page.replace("{TEXT_FILE}", TEXT_FILE)
        self.wfile.write(editor_page.encode("utf-8"))

    def send_main_page(self, query_params):
        """Send the main troubleshooting page with simple sections"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        success_msg = ""
        if 'msg' in query_params:
            msg_text = query_params['msg'][0] if query_params['msg'] else ""
            success_msg = f'<div class="alert alert-success" role="alert">✓ {html.escape(msg_text)}</div>'

        app_sections = self.load_sections()
        last_updated = ''
        if os.path.exists(TEXT_FILE):
            try:
                mtime = os.path.getmtime(TEXT_FILE)
                last_updated = '<em>Last updated: ' + html.escape(
                    __import__('datetime').datetime.fromtimestamp(mtime)
                    .strftime('%Y-%m-%d %H:%M:%S')
                ) + '</em>'
            except Exception:
                last_updated = ''
        if app_sections:

            # Build plain sections
            options = ['<option value="__all__">All applications</option>']
            section_html_list = []
            
            for idx, (name, body) in enumerate(app_sections):
                slug = f"app{idx}"
                options.append(f'<option value="{slug}">{html.escape(name)}</option>')
                formatted = self.format_content(body)
                error_count = len(re.findall(r'- \*\*Error\*\*:|^- \*\*', body, re.MULTILINE))
                badge = f'<span class="error-badge">{error_count}</span>' if error_count > 0 else '<span class="info-badge">ℹ</span>'
                section_html_list.append(f'<div class="section" data-app="{slug}"><h2>{html.escape(name)} {badge}</h2>{formatted}</div>')
            
            sections_html = "\n".join(section_html_list)
            select_html = '<select id="appSelect" onchange="filterApp()">' + "\n".join(options) + '</select>'
        else:
            select_html = ''
            sections_html = '<div class="section"><p><em>No troubleshooting steps available yet.</em></p></div>'

        page = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Troubleshooting Guide</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header class="header">
    <h1>🔧 Troubleshooting Guide</h1>
    <p class="subtitle">Error codes, solutions & quick reference</p>
</header>
<div class="last-updated">
    {last_updated}
</div>

{success_msg}

<div class="container">
    <div class="controls-section">
        <div class="control-group">
            <label for="appSelect">📂 Filter by Application:</label>
            {select_html}
        </div>
        <div class="control-group">
            <label for="searchBox">🔍 Search:</label>
            <input type="text" id="searchBox" placeholder="Type error code, error name, or keyword..." onkeyup="performSearch()" autocomplete="off">
            <div id="searchResults" class="search-results" style="display: none;"></div>
            <button id="collapseAll" class="small-btn" title="Collapse all sections">Collapse all</button>
            <button id="expandAll" class="small-btn" title="Expand all sections">Expand all</button>
            <button id="darkModeToggle" class="small-btn" title="Toggle dark mode">🌙</button>
        </div>
    </div>
    
    <div id="sections" class="sections-container">
        {sections_html}
    </div>
</div>

<footer>
    <p><a href="/editor">📝 Edit Content</a></p>
</footer>

<script>
const searchBox = document.getElementById('searchBox');
let searchTimeout;

// utility to escape regex
function escapeRegex(s) {
    return s.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\$&');
}

// highlight occurrences of term inside element
function highlightTerm(el, term) {
    if (!term) return;
    const regex = new RegExp(`(${escapeRegex(term)})`, 'gi');
    el.innerHTML = el.innerHTML.replace(/<mark>(.*?)<\/mark>/gi, '$1'); // remove previous highlights
    el.innerHTML = el.innerHTML.replace(regex, '<mark>$1</mark>');
}

// keep original HTML so we can restore or filter individual sections
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.section').forEach(sec => {
        sec.dataset.original = sec.innerHTML;
    });
    // attach collapse behaviour to headers
    document.querySelectorAll('.section h2').forEach(h2 => {
        h2.addEventListener('click', () => {
            h2.closest('.section').classList.toggle('collapsed');
        });
    });
    // collapse/expand all buttons
    document.getElementById('collapseAll').addEventListener('click', () => {
        document.querySelectorAll('.section').forEach(sec => sec.classList.add('collapsed'));
    });
    document.getElementById('expandAll').addEventListener('click', () => {
        document.querySelectorAll('.section').forEach(sec => sec.classList.remove('collapsed'));
    });
    // dark mode toggle
    const dm = document.getElementById('darkModeToggle');
    dm.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
    });
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
    }
    // back-to-top
    const topBtn = document.createElement('button');
    topBtn.id = 'backToTop';
    topBtn.className = 'back-to-top';
    topBtn.textContent = '↑ Top';
    topBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    document.body.appendChild(topBtn);
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 200) topBtn.classList.add('show');
        else topBtn.classList.remove('show');
    });
});

function performSearch() {
    clearTimeout(searchTimeout);
    const term = searchBox.value.trim().toLowerCase();
    const sections = document.querySelectorAll('.section');
    let visibleCount = 0;

    if (term.length < 1) {
        sections.forEach(section => {
            section.innerHTML = section.dataset.original;
            section.style.display = '';
            visibleCount++;
        });
        document.getElementById('searchResults').style.display = 'none';
        return;
    }

    // ask server for a list of matching apps/snippets and show clickable suggestions
    if (term.length > 1) {
        fetch(`/api/search?q=${encodeURIComponent(term)}`)
            .then(r => r.json())
            .then(data => {
                const resDiv = document.getElementById('searchResults');
                if (data.count > 0) {
                    resDiv.innerHTML = data.results.map(r => {
                        const txt = r.snippet || r.summary;
                        return `<div class="search-item" data-slug="${r.slug}"><strong>${r.app}</strong>: ${txt}</div>`;
                    }).join('');
                    resDiv.style.display = 'block';
                    resDiv.querySelectorAll('.search-item').forEach(item => {
                        item.addEventListener('click', () => {
                            const target = document.querySelector(`.section[data-app="${item.dataset.slug}"]`);
                            if (target) {
                                target.scrollIntoView({behavior: 'smooth'});
                                target.classList.add('highlight');
                                setTimeout(() => target.classList.remove('highlight'), 2000);
                            }
                            resDiv.style.display = 'none';
                        });
                    });
                } else {
                    resDiv.innerHTML = '<div class="search-header">No matches found</div>';
                    resDiv.style.display = 'block';
                }
            });
    }

    searchTimeout = setTimeout(() => {
        sections.forEach(section => {
            // restore original HTML for fresh filtering
            section.innerHTML = section.dataset.original;
            const title = section.querySelector('h2')?.textContent?.toLowerCase() || '';
            let matched = false;

            if (title.includes(term)) {
                matched = true;
            }

            // narrow down individual elements (headings, paragraphs, list items)
            section.querySelectorAll('h3, h4, p, li').forEach(el => {
                if (!el.textContent.toLowerCase().includes(term)) {
                    el.remove();
                } else {
                    matched = true;
                }
            });
            // clean up any empty lists after removing items
            section.querySelectorAll('ul').forEach(ul => {
                if (ul.querySelectorAll('li').length === 0) {
                    ul.remove();
                }
            });

            if (matched) {
                section.style.display = '';
                visibleCount++;
                highlightTerm(section, term);
            } else {
                section.style.display = 'none';
            }
        });

        if (visibleCount === 0) {
            document.getElementById('searchResults').innerHTML = '<div class="search-header">No matches found</div>';
            document.getElementById('searchResults').style.display = 'block';
        } else {
            document.getElementById('searchResults').style.display = 'none';
        }
    }, 200);
}

function filterApp() {{
    const val = document.getElementById('appSelect').value;
    const sections = document.querySelectorAll('.section');
    
    sections.forEach(section => {{
        const appId = section.dataset.app;
        if (val === '__all__' || appId === val) {{
            section.style.display = '';
        }} else {{
            section.style.display = 'none';
        }}
    }});
}}

// Close search results on Escape
document.addEventListener('keydown', (e) => {{
    if (e.key === 'Escape') {{
        document.getElementById('searchResults').style.display = 'none';
    }}
}});
</script>
</body>
</html>"""
        # insert dynamic content into placeholders
        page = page.replace("{success_msg}", success_msg)
        page = page.replace("{select_html}", select_html)
        page = page.replace("{sections_html}", sections_html)
        page = page.replace("{last_updated}", last_updated)
        self.wfile.write(page.encode("utf-8"))


    def format_content(self, content):
        """Format content with HTML structure, rendering bullets and bold text."""
        lines = content.split('\n')
        html_parts = []
        list_open = False

        def close_list():
            nonlocal list_open
            if list_open:
                html_parts.append('</ul>')
                list_open = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('### '):
                close_list()
                html_parts.append(f'<h4>{html.escape(stripped[4:])}</h4>')
            elif stripped.startswith('## '):
                close_list()
                html_parts.append(f'<h3>{html.escape(stripped[3:])}</h3>')
            elif stripped.startswith('- '):
                # bullet item
                if not list_open:
                    html_parts.append('<ul>')
                    list_open = True
                item = stripped[2:]
                # convert **bold** to <strong>
                item = html.escape(item)
                item = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item)
                html_parts.append(f'<li>{item}</li>')
            elif stripped:
                close_list()
                txt = html.escape(stripped)
                txt = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', txt)
                html_parts.append(f'<p>{txt}</p>')
        close_list()
        return '\n'.join(html_parts)

    def send_css(self):
        """Send CSS file or inline default"""
        if os.path.exists('style.css'):
            self.send_response(200)
            self.send_header('Content-type', 'text/css; charset=utf-8')
            self.end_headers()
            with open('style.css', 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/css; charset=utf-8')
            self.end_headers()
            css = self.get_default_css()
            self.wfile.write(css.encode('utf-8'))

    def get_default_css(self):
        """Default mobile-first CSS"""
        return """/* Mobile-first responsive troubleshooting guide */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --primary: #0066cc;
    --primary-dark: #0052a3;
    --success: #28a745;
    --danger: #dc3545;
    --warning: #ffc107;
    --info: #17a2b8;
    --light: #f8f9fa;
    --dark: #343a40;
    --border: #ddd;
    --text: #333;
}

/* dark mode overrides */
body.dark-mode {
    background: #222;
    color: #ddd;
}
body.dark-mode a { color: var(--primary); }
body.dark-mode .header { background: #111; }
body.dark-mode .section { background: #333; }
body.dark-mode .controls-section { background: #222; }
body.dark-mode input, body.dark-mode select { background: #444; color: #eee; border-color: #555; }
body.dark-mode .search-results { background: #444; border-color: #555; color: #eee; }
body.dark-mode .search-header { background: #333; color: #ffc107; }

/* sticky header */
.header {
    position: sticky;
    top: 0;
    z-index: 1000;
}

/* collapse/expand styling */
.section.collapsed > *:not(h2) {
    display: none;
}
.section h2 {
    cursor: pointer;
}

/* control buttons */
.small-btn {
    font-size: 0.85em;
    padding: 0.3em 0.6em;
    margin-left: 0.3em;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: white;
    cursor: pointer;
}
.small-btn:hover { background: var(--light); }

/* back to top */
.back-to-top {
    position: fixed;
    bottom: 1em;
    right: 1em;
    padding: 0.6em 0.9em;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: 4px;
    display: none;
    cursor: pointer;
    z-index: 1001;
}
.back-to-top.show { display: block; }

/* print styles */
@media print {
    .controls-section, .header, .back-to-top { display: none !important; }
    .section { page-break-inside: avoid; }
}

html, body {
    height: 100%;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: var(--text);
    background: #f5f5f5;
}

.header {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
    padding: 1.5em 1em;
    text-align: center;
}

.header h1 {
    font-size: 1.8em;
    margin-bottom: 0.3em;
}

.header p {
    font-size: 0.9em;
    opacity: 0.95;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1em;
}

.controls-section {
    background: white;
    padding: 1em;
    border-radius: 8px;
    margin-bottom: 1.5em;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.control-group {
    margin-bottom: 1em;
}

.control-group:last-child {
    margin-bottom: 0;
}

.control-group label {
    display: block;
    font-weight: 600;
    margin-bottom: 0.5em;
    color: var(--dark);
}

.control-group select,
.control-group input {
    width: 100%;
    padding: 0.75em;
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: 1em;
    background: white;
    color: var(--text);
}

.control-group input:focus,
.control-group select:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(0,102,204,0.1);
}

.sections-container {
    animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.section {
    background: white;
    border-radius: 8px;
    padding: 1.2em;
    margin-bottom: 1.5em;
    transition: all 0.3s ease;
}

.section h2 {
    font-size: 1.2em;
    color: var(--primary);
    margin-top: 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.error-badge {
    background: var(--danger);
    color: white;
    padding: 0.3em 0.7em;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 600;
    white-space: nowrap;
}

.info-badge {
    background: var(--info);
    color: white;
    padding: 0.3em 0.7em;
    border-radius: 20px;
    font-size: 0.85em;
}

.section h3 {
    font-size: 1.1em;
    color: var(--dark);
    margin: 1.2em 0 0.7em 0;
    padding-bottom: 0.5em;
    border-bottom: 1px solid var(--border);
}

.section h3:first-child {
    margin-top: 0;
}

.section h4 {
    font-size: 1em;
    color: var(--primary);
    margin: 1em 0 0.5em 0;
}

.section p {
    margin: 0.5em 0;
    line-height: 1.5;
}

.section ul {
    margin: 0.5em 0 1em 1.4em;
    padding-left: 0;
    list-style: disc;
}

.section li {
    margin: 0.3em 0;
    line-height: 1.4;
}

/* legacy error-item class is no longer generated, but keep for any manual entries */
.error-item {
    background: #f8f9fa;
    padding: 0.8em;
    margin: 0.7em 0;
    border-left: 3px solid var(--danger);
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
    line-height: 1.5;
    overflow-x: auto;
}

.alert {
    padding: 1em;
    margin-bottom: 1em;
    border-radius: 4px;
    border-left: 4px solid;
}

.alert-success {
    background: #d4edda;
    border-color: var(--success);
    color: #155724;
}

.search-results {
    margin-top: 0.5em;
    background: white;
    border: 1px solid var(--border);
    border-radius: 4px;
    max-height: 200px;
    overflow-y: auto;
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.search-header {
    padding: 0.7em 1em;
    background: var(--light);
    font-weight: 600;
    border-bottom: 1px solid var(--border);
    color: var(--danger);
}
.search-item {
    padding: 0.6em 1em;
    cursor: pointer;
}
.search-item:hover { background: var(--light); }

/* highlight class used when suggestion clicked */
.highlight {
    animation: pulse 1.5s ease-out;
}
@keyframes pulse {
    0% { background: yellow; }
    100% { background: transparent; }
}

footer {
    text-align: center;
    padding: 2em 1em;
    color: #666;
    font-size: 0.9em;
}

footer a {
    color: var(--primary);
    text-decoration: none;
}

footer a:hover {
    text-decoration: underline;
}

/* Tablet */
@media (min-width: 768px) {
    .container {
        padding: 2em;
    }
    
    /* removed grid layout for sections */
    
    .control-group {
        display: inline-block;
        width: calc(50% - 0.5em);
        margin-right: 1em;
        margin-bottom: 0;
        vertical-align: top;
    }
    
    .control-group:nth-child(even) {
        margin-right: 0;
    }
}

/* Desktop */
@media (min-width: 1024px) {
    /* no additional desktop layout required for sections */
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
    * {
        animation: none !important;
        transition: none !important;
    }
}
"""

    def do_POST(self):
        """Handle POST requests"""
        from urllib.parse import urlparse
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == "/editor":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                params = urllib.parse.parse_qs(body)
                
                if 'action' in params and params['action'][0] == 'save_full':
                    full_content = params.get('fullContent', [''])[0]
                    with open(TEXT_FILE, 'w', encoding='utf-8') as f:
                        f.write(full_content)
                    redirect_url = "/?msg=Content saved successfully"
                else:
                    app_name = params.get('appName', [''])[0].strip()
                    app_steps = params.get('appSteps', [''])[0].strip()
                    
                    if app_name:
                        with open(TEXT_FILE, 'a', encoding='utf-8') as f:
                            f.write(f"\n\n# {app_name}\n\n{app_steps}\n")
                        redirect_url = f"/?msg=Added: {urllib.parse.quote(app_name)}"
                    else:
                        redirect_url = "/?msg=Application name required"
                
                self.send_response(303)
                self.send_header('Location', redirect_url)
                self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(f"Error: {str(e)}".encode('utf-8'))
        else:
            self.send_error(405)

def run():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, TroubleshootHandler)
    print(f"🚀 Server running on http://localhost:{PORT}/")
    print(f"📝 Editor: http://localhost:{PORT}/editor")
    print(f"Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    finally:
        httpd.server_close()

if __name__ == '__main__':
    run()
