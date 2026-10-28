"""
Proximity Search API Web Service
Exposes /search/ endpoint for nearest location queries on a 1x1 grid network.
Supports road network linkage graphs (link.txt) for realistic grid traversal distance.
"""

import os
from flask import Flask, request, jsonify, render_template_string
from engine import ProximitySearchEngine

app = Flask(__name__)

# Initialize search engine with locations dataset and default road network links
CSV_PATH = os.environ.get('DATA_CSV_PATH', os.path.join(os.path.dirname(__file__), 'locations.csv'))
if not os.path.exists(CSV_PATH):
    CSV_PATH = os.path.join(os.path.dirname(__file__), 'locations.csv')

LINK_PATH = os.environ.get('DEFAULT_LINK_PATH', os.path.join(os.path.dirname(__file__), 'link.txt'))
if not os.path.exists(LINK_PATH):
    LINK_PATH = os.path.join(os.path.dirname(__file__), 'link.txt')

engine = ProximitySearchEngine(csv_path=CSV_PATH, default_link_path=LINK_PATH, grid_size=20)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'total_locations': len(engine.locations),
        'categories': sorted(list(engine.by_category.keys())),
        'default_link_loaded': bool(engine.default_link_path and os.path.exists(engine.default_link_path))
    }), 200


@app.route('/search/', methods=['GET', 'POST'])
@app.route('/search', methods=['GET', 'POST'])
def search_locations():
    """
    Primary Proximity Search Endpoint.
    
    Accepts:
        lat (float): Current Latitude
        long (float): Current Longitude
        cat (str): CategorySearch
        rad (float): Search Radius (circular Euclidean distance)
        link (file / str / URL): Road network linkage information (optional, defaults to link.txt)
    
    Returns:
        List[int]: Array of up to 10 location IDs sorted by grid traversal distance.
    """
    data = {}
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()
    
    params = {**data, **request.args.to_dict()}
    
    # Extract fields with support for aliases
    lat_raw = (params.get('lat') or 
               params.get('latitude') or 
               params.get('Current Latitude'))
    
    long_raw = (params.get('long') or 
                params.get('lng') or 
                params.get('longitude') or 
                params.get('Current Longitude'))
    
    cat_raw = (params.get('cat') or 
               params.get('category') or 
               params.get('CategorySearch') or 
               params.get('categorySearch'))
    
    rad_raw = (params.get('rad') or 
               params.get('radius') or 
               params.get('Radius'))

    # Extract linkage info (supports file upload, file path, URL, or raw text)
    link_file = request.files.get('link') or request.files.get('linkage')
    link_val = link_file or (params.get('link') or 
                             params.get('linkage') or 
                             params.get('link_info') or 
                             params.get('linkage info'))

    if lat_raw is None or long_raw is None or cat_raw is None or rad_raw is None:
        return jsonify({
            'error': 'Missing required parameters. Required fields: lat, long, cat, rad (optional: link).',
            'received': params
        }), 400

    try:
        lat = float(lat_raw)
        long_ = float(long_raw)
        rad = float(rad_raw)
        cat = str(cat_raw).strip()
    except (ValueError, TypeError):
        return jsonify({
            'error': 'Invalid parameter format. lat, long, and rad must be numeric.'
        }), 400

    if rad <= 0:
        return jsonify({'error': 'Radius must be greater than 0.'}), 400

    # Execute search with graph BFS traversal
    results = engine.search(lat=lat, long_=long_, cat=cat, rad=rad, link=link_val, k=10)

    # Optional dictionary wrapper if requested explicitly via format=dict
    format_type = params.get('format', '').lower()
    if format_type in ('dict', 'object', 'json_object'):
        response = jsonify({
            'recommended_locations': results,
            'count': len(results),
            'query': {
                'lat': lat,
                'long': long_,
                'cat': cat,
                'rad': rad,
                'link': str(link_val) if link_val else 'default'
            }
        })
    else:
        # Standard required format: 10 recommended location IDs
        response = jsonify(results)

    response.headers['X-Location-IDs'] = ','.join(map(str, results))
    return response, 200


@app.route('/', methods=['GET'])
def index():
    """Interactive documentation and query testing interface."""
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    if best == 'application/json' and request.accept_mimetypes[best] > request.accept_mimetypes['text/html']:
        return jsonify({
            'api': 'Proximity Search API',
            'endpoint': '/search/',
            'fields': ['lat', 'long', 'cat', 'rad', 'link'],
            'categories': sorted(list(engine.by_category.keys())),
            'total_locations': len(engine.locations)
        })

    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Proximity Search API - Lab 7</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #4f46e5;
                --primary-hover: #4338ca;
                --bg: #0f172a;
                --card-bg: #1e293b;
                --text-main: #f8fafc;
                --text-sub: #94a3b8;
                --accent: #10b981;
                --border: #334155;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: 'Inter', sans-serif;
                background-color: var(--bg);
                color: var(--text-main);
                padding: 40px 20px;
                min-height: 100vh;
            }
            .container {
                max-width: 820px;
                margin: 0 auto;
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
            }
            .header h1 {
                font-size: 2.2rem;
                font-weight: 700;
                background: linear-gradient(135deg, #a5b4fc, #818cf8, #6366f1);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 8px;
            }
            .header p {
                color: var(--text-sub);
                font-size: 1.05rem;
            }
            .badge {
                display: inline-block;
                background: rgba(16, 185, 129, 0.15);
                color: #34d399;
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 9999px;
                padding: 4px 12px;
                font-size: 0.85rem;
                font-weight: 600;
                margin-top: 10px;
            }
            .card {
                background-color: var(--card-bg);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 28px;
                margin-bottom: 24px;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            }
            .card-title {
                font-size: 1.25rem;
                font-weight: 600;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .form-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
            }
            .form-group {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            .form-group.full {
                grid-column: 1 / -1;
            }
            label {
                font-size: 0.875rem;
                font-weight: 500;
                color: var(--text-sub);
            }
            input, select {
                background-color: #0b1120;
                border: 1px solid var(--border);
                color: var(--text-main);
                padding: 10px 14px;
                border-radius: 8px;
                font-size: 0.95rem;
                outline: none;
                transition: border-color 0.2s;
            }
            input:focus, select:focus {
                border-color: var(--primary);
            }
            .btn {
                background-color: var(--primary);
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
                margin-top: 8px;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 8px;
            }
            .btn:hover {
                background-color: var(--primary-hover);
            }
            pre {
                background-color: #0b1120;
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 16px;
                color: #e2e8f0;
                font-family: 'Consolas', monospace;
                font-size: 0.95rem;
                overflow-x: auto;
                max-height: 250px;
            }
            .output-box {
                margin-top: 20px;
                display: none;
            }
            .latency-tag {
                float: right;
                font-size: 0.85rem;
                color: #38bdf8;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Proximity Search API</h1>
                <p>1x1 Grid Road Network Shortest Path Proximity Engine</p>
                <div class="badge">Live &amp; Operational</div>
            </div>

            <div class="card">
                <div class="card-title">Interactive Query Console</div>
                <form id="searchForm">
                    <div class="form-grid">
                        <div class="form-group">
                            <label for="lat">Current Latitude (lat) [0.0 - 1.0]</label>
                            <input type="number" step="any" id="lat" name="lat" value="0.505051" required>
                        </div>
                        <div class="form-group">
                            <label for="long">Current Longitude (long) [0.0 - 1.0]</label>
                            <input type="number" step="any" id="long" name="long" value="0.505051" required>
                        </div>
                        <div class="form-group">
                            <label for="cat">CategorySearch (cat)</label>
                            <select id="cat" name="cat" required>
                                <option value="cafe" selected>cafe</option>
                                <option value="bank">bank</option>
                                <option value="store">store</option>
                                <option value="pharmacy">pharmacy</option>
                                <option value="hospital">hospital</option>
                                <option value="school">school</option>
                                <option value="restaurant">restaurant</option>
                                <option value="park">park</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="rad">Radius (rad)</label>
                            <input type="number" step="any" id="rad" name="rad" value="0.15" required>
                        </div>
                        <div class="form-group full">
                            <label for="link">Road Network Linkage Info (link) [File path, URL, or blank for default link.txt]</label>
                            <input type="text" id="link" name="link" value="link.txt" placeholder="link.txt or URL or upload">
                        </div>
                    </div>
                    <button type="submit" class="btn" id="submitBtn" style="width: 100%;">
                        Execute Proximity Search (/search/)
                    </button>
                </form>

                <div class="output-box" id="output">
                    <div style="margin-bottom: 8px;">
                        <strong>Response Output:</strong>
                        <span class="latency-tag" id="timeTaken"></span>
                    </div>
                    <pre><code id="resultJson"></code></pre>
                </div>
            </div>
        </div>

        <script>
            document.getElementById('searchForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                const btn = document.getElementById('submitBtn');
                btn.disabled = true;
                btn.innerText = 'Calculating...';

                const lat = document.getElementById('lat').value;
                const long = document.getElementById('long').value;
                const cat = document.getElementById('cat').value;
                const rad = document.getElementById('rad').value;
                const link = document.getElementById('link').value;

                let url = `/search/?lat=${encodeURIComponent(lat)}&long=${encodeURIComponent(long)}&cat=${encodeURIComponent(cat)}&rad=${encodeURIComponent(rad)}`;
                if (link && link.trim() !== '') {
                    url += `&link=${encodeURIComponent(link.trim())}`;
                }
                
                const t0 = performance.now();
                try {
                    const res = await fetch(url);
                    const t1 = performance.now();
                    const data = await res.json();
                    
                    document.getElementById('output').style.display = 'block';
                    document.getElementById('timeTaken').innerText = `Latency: ${(t1 - t0).toFixed(2)} ms`;
                    document.getElementById('resultJson').innerText = JSON.stringify(data, null, 2);
                } catch(err) {
                    document.getElementById('output').style.display = 'block';
                    document.getElementById('timeTaken').innerText = 'Error';
                    document.getElementById('resultJson').innerText = err.toString();
                } finally {
                    btn.disabled = false;
                    btn.innerText = 'Execute Proximity Search (/search/)';
                }
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(html)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
