"""
Core proximity search engine for Lab 7.
Implements spatial indexing and road network graph shortest-path traversal.
Handles missing road links via Breadth-First Search (BFS) on the 1x1 grid network.
"""

import os
import csv
import math
import hashlib
import urllib.request
from collections import defaultdict, deque


class ProximitySearchEngine:
    def __init__(self, csv_path='locations.csv', default_link_path='link.txt', grid_size=20):
        self.csv_path = csv_path
        self.default_link_path = default_link_path
        self.grid_size = grid_size
        self.cell_w = 1.0 / grid_size
        
        # Primary storage: id -> (id, lat, long, category, node_idx)
        self.locations = {}
        # Category partition: category -> list of (id, lat, long, category, node_idx)
        self.by_category = defaultdict(list)
        # 2D spatial bucket index: (category, cx, cy) -> list of (id, lat, long, category, node_idx)
        self.spatial_index = defaultdict(list)
        
        # Cache for parsed graphs: cache_key -> adj_list (list of lists of size 10000)
        self.graph_cache = {}
        
        self.load_data(csv_path)
        
        # Pre-cache default link graph if link.txt is available
        if default_link_path and os.path.exists(default_link_path):
            self.get_or_load_graph(default_link_path)

    def load_data(self, csv_path):
        """Loads and indexes locations from CSV file."""
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                loc_id = int(row['ID'])
                lat = float(row['Latitude'])
                long_ = float(row['Longitude'])
                cat = row['Category'].strip().lower()
                
                # Each location in 100x100 grid corresponds to node index
                i = max(0, min(99, round(lat * 99)))
                j = max(0, min(99, round(long_ * 99)))
                node_idx = i * 100 + j
                
                loc = (loc_id, lat, long_, cat, node_idx)
                self.locations[loc_id] = loc
                self.by_category[cat].append(loc)
                
                cx = min(max(0, int(lat / self.cell_w)), self.grid_size - 1)
                cy = min(max(0, int(long_ / self.cell_w)), self.grid_size - 1)
                self.spatial_index[(cat, cx, cy)].append(loc)

    def parse_graph_lines(self, lines):
        """
        Parses linkage lines into an adjacency list for the 10,000 grid nodes.
        Supports both:
          1. 'Longitude_A Latitude_A Longitude_B Latitude_B' (4 floats)
          2. 'ID_A ID_B' (2 integers, 1-indexed)
        """
        adj = [[] for _ in range(10000)]
        for line in lines:
            if isinstance(line, bytes):
                line = line.decode('utf-8-sig', errors='ignore')
            line = line.strip().lstrip('\ufeff')
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 4:
                try:
                    lonA, latA, lonB, latB = float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
                    jA, iA = max(0, min(99, round(lonA * 99))), max(0, min(99, round(latA * 99)))
                    jB, iB = max(0, min(99, round(lonB * 99))), max(0, min(99, round(latB * 99)))
                    u = iA * 100 + jA
                    v = iB * 100 + jB
                    adj[u].append(v)
                    adj[v].append(u)
                except ValueError:
                    continue
            elif len(parts) == 2:
                try:
                    idA, idB = int(parts[0]), int(parts[1])
                    if 1 <= idA <= 10000 and 1 <= idB <= 10000:
                        u = idA - 1
                        v = idB - 1
                        adj[u].append(v)
                        adj[v].append(u)
                except ValueError:
                    continue
        return adj

    def get_or_load_graph(self, link_input):
        """
        Retrieves or constructs the graph adjacency list from various link input types:
        - None / empty: falls back to default_link_path if it exists
        - File path string
        - HTTP/HTTPS URL
        - Raw text content
        - FileStorage or bytes/stream
        """
        if not link_input:
            if self.default_link_path and os.path.exists(self.default_link_path):
                link_input = self.default_link_path
            else:
                return None

        # Check if link_input is a local file path
        if isinstance(link_input, str):
            base_dir = os.path.dirname(os.path.abspath(self.csv_path))
            candidate_path = os.path.join(base_dir, link_input) if not os.path.isabs(link_input) else link_input
            
            if os.path.isfile(candidate_path):
                mtime = os.path.getmtime(candidate_path)
                cache_key = f"file:{candidate_path}:{mtime}"
                if cache_key in self.graph_cache:
                    return self.graph_cache[cache_key]
                with open(candidate_path, 'r', encoding='utf-8-sig') as f:
                    adj = self.parse_graph_lines(f)
                self.graph_cache[cache_key] = adj
                return adj

            if os.path.isfile(link_input):
                mtime = os.path.getmtime(link_input)
                cache_key = f"file:{link_input}:{mtime}"
                if cache_key in self.graph_cache:
                    return self.graph_cache[cache_key]
                with open(link_input, 'r', encoding='utf-8-sig') as f:
                    adj = self.parse_graph_lines(f)
                self.graph_cache[cache_key] = adj
                return adj

            # Check if it's a URL
            if link_input.startswith('http://') or link_input.startswith('https://'):
                cache_key = f"url:{link_input}"
                if cache_key in self.graph_cache:
                    return self.graph_cache[cache_key]
                try:
                    req = urllib.request.Request(link_input, headers={'User-Agent': 'ProximitySearch/1.0'})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        content = resp.read().decode('utf-8-sig', errors='ignore')
                        adj = self.parse_graph_lines(content.splitlines())
                        self.graph_cache[cache_key] = adj
                        return adj
                except Exception as e:
                    print(f"Failed to fetch link URL: {e}")
                    return None

            # Raw string content
            content_hash = hashlib.md5(link_input.encode('utf-8')).hexdigest()
            cache_key = f"raw:{content_hash}"
            if cache_key in self.graph_cache:
                return self.graph_cache[cache_key]
            adj = self.parse_graph_lines(link_input.splitlines())
            self.graph_cache[cache_key] = adj
            return adj

        # FileStorage / file-like / bytes
        if hasattr(link_input, 'read'):
            raw_data = link_input.read()
            if hasattr(link_input, 'seek'):
                link_input.seek(0)
            if isinstance(raw_data, bytes):
                raw_text = raw_data.decode('utf-8-sig', errors='ignore')
            else:
                raw_text = str(raw_data)
            content_hash = hashlib.md5(raw_text.encode('utf-8')).hexdigest()
            cache_key = f"raw:{content_hash}"
            if cache_key in self.graph_cache:
                return self.graph_cache[cache_key]
            adj = self.parse_graph_lines(raw_text.splitlines())
            self.graph_cache[cache_key] = adj
            return adj

        return None

    def search(self, lat, long_, cat, rad, link=None, k=10):
        """
        Finds the k closest locations matching category within circular radius.
        
        - Circular filter: Euclidean distance from (lat, long_) <= rad
        - Distance metric: Actual traversal distance on grid road network (via link graph BFS)
        - Fallback metric: Manhattan distance |x - lat| + |y - long_| if no link graph available
        - Canonical tie-breaker: Ascending location ID
        """
        cat = cat.strip().lower()
        if cat not in self.by_category:
            return []

        rad_sq = rad * rad + 1e-12
        
        # Spatial filtering: extract candidate locations within circular radius
        min_cx = max(0, int((lat - rad) / self.cell_w))
        max_cx = min(self.grid_size - 1, int((lat + rad) / self.cell_w))
        min_cy = max(0, int((long_ - rad) / self.cell_w))
        max_cy = min(self.grid_size - 1, int((long_ + rad) / self.cell_w))

        valid_candidates = []
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                bucket = self.spatial_index.get((cat, cx, cy))
                if not bucket:
                    continue
                for loc_id, l_lat, l_long, _, node_idx in bucket:
                    dx = l_lat - lat
                    dy = l_long - long_
                    circ_dist_sq = dx * dx + dy * dy
                    if circ_dist_sq <= rad_sq:
                        valid_candidates.append((loc_id, l_lat, l_long, node_idx))

        if not valid_candidates:
            return []

        # Obtain road network graph
        adj = self.get_or_load_graph(link)

        ranked = []
        if adj is not None:
            # Query origin node on 100x100 grid
            i0 = max(0, min(99, round(lat * 99)))
            j0 = max(0, min(99, round(long_ * 99)))
            start_node = i0 * 100 + j0
            
            # Continuous offset from query coords to start grid node
            start_offset = abs(lat - i0 / 99.0) + abs(long_ - j0 / 99.0)
            step_length = 1.0 / 99.0

            # BFS to find shortest path steps on unweighted road network graph
            dist = [-1] * 10000
            dist[start_node] = 0
            q = deque([start_node])
            
            while q:
                u = q.popleft()
                d = dist[u] + 1
                for v in adj[u]:
                    if dist[v] == -1:
                        dist[v] = d
                        q.append(v)

            for loc_id, l_lat, l_long, node_idx in valid_candidates:
                steps = dist[node_idx]
                dx = l_lat - lat
                dy = l_long - long_
                circ_dist_sq = dx * dx + dy * dy
                if steps != -1:
                    # Reachable along road network
                    traversal_dist = start_offset + steps * step_length
                else:
                    # Unreachable due to disconnected components
                    traversal_dist = float('inf')
                ranked.append((traversal_dist, circ_dist_sq, loc_id))
        else:
            # Fallback to ideal grid Manhattan distance if no graph provided
            for loc_id, l_lat, l_long, _ in valid_candidates:
                dx = l_lat - lat
                dy = l_long - long_
                circ_dist_sq = dx * dx + dy * dy
                grid_dist = abs(dx) + abs(dy)
                ranked.append((grid_dist, circ_dist_sq, loc_id))

        # Sort primarily by traversal distance, then circular distance, then ID
        ranked.sort(key=lambda item: (item[0], item[1], item[2]))
        return [item[2] for item in ranked[:k]]

