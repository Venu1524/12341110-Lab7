"""
Zero-dependency standalone server for Proximity Search API.
Uses Python standard library (http.server) to run without external dependencies.
"""

import os
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from engine import ProximitySearchEngine

CSV_PATH = os.path.join(os.path.dirname(__file__), 'locations.csv')
engine = ProximitySearchEngine(csv_path=CSV_PATH, grid_size=20)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class ProximityRequestHandler(BaseHTTPRequestHandler):
    def send_json(self, status_code, data, extra_headers=None):
        payload = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Access-Control-Allow-Origin', '*')
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, str(v))
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/') + '/'
        
        if path == '/health/':
            return self.send_json(200, {
                'status': 'healthy',
                'total_locations': len(engine.locations)
            })

        if path == '/search/':
            params = dict(urllib.parse.parse_qsl(parsed.query))
            return self.handle_search(params)

        # Default info
        return self.send_json(200, {
            'api': 'Proximity Search API (Standalone)',
            'endpoint': '/search/',
            'fields': ['lat', 'long', 'cat', 'rad']
        })

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip('/') + '/'

        if path == '/search/':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ''
            
            content_type = self.headers.get('Content-Type', '')
            params = {}
            if 'application/json' in content_type and body:
                try:
                    params = json.loads(body)
                except Exception:
                    return self.send_json(400, {'error': 'Invalid JSON body'})
            elif body:
                params = dict(urllib.parse.parse_qsl(body))

            # Merge with query params if any
            query_params = dict(urllib.parse.parse_qsl(parsed.query))
            params = {**query_params, **params}
            return self.handle_search(params)

        return self.send_json(404, {'error': 'Not found'})

    def handle_search(self, params):
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

        if lat_raw is None or long_raw is None or cat_raw is None or rad_raw is None:
            return self.send_json(400, {
                'error': 'Missing required fields. Required: lat, long, cat, rad.',
                'received': params
            })

        try:
            lat = float(lat_raw)
            long_ = float(long_raw)
            rad = float(rad_raw)
            cat = str(cat_raw).strip()
        except (ValueError, TypeError):
            return self.send_json(400, {'error': 'lat, long, rad must be numeric.'})

        if rad <= 0:
            return self.send_json(400, {'error': 'Radius must be greater than 0.'})

        link = (params.get('link') or 
                params.get('linkage') or 
                params.get('link_info') or 
                params.get('linkage info'))

        results = engine.search(lat=lat, long_=long_, cat=cat, rad=rad, link=link, k=10)

        format_type = params.get('format', '').lower()
        extra_headers = {'X-Location-IDs': ','.join(map(str, results))}
        
        if format_type in ('dict', 'object', 'json_object'):
            return self.send_json(200, {
                'recommended_locations': results,
                'count': len(results)
            }, extra_headers)
        
        return self.send_json(200, results, extra_headers)

    def log_message(self, format, *args):
        # Concise logging
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_standalone(host='0.0.0.0', port=5000):
    server = ThreadedHTTPServer((host, port), ProximityRequestHandler)
    print(f"Serving Proximity Search API on http://{host}:{port}/search/ (Zero Dependencies)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    run_standalone(port=port)
