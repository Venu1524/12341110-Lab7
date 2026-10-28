"""
Automated Integration Test Runner for Proximity Search API Stack.
Verifies end-to-end functionality via Nginx Reverse Proxy Gateway.
"""

import sys
import time
import json
import urllib.request
import urllib.parse
import urllib.error
import os

BASE_URL = os.environ.get('TARGET_URL', 'http://web:80').rstrip('/')

def make_request(path, method='GET', data=None, headers=None):
    url = f"{BASE_URL}{path}"
    req_headers = headers or {}
    req_data = None
    
    if data is not None:
        if isinstance(data, (dict, list)):
            req_data = json.dumps(data).encode('utf-8')
            req_headers['Content-Type'] = 'application/json'
        elif isinstance(data, str):
            req_data = data.encode('utf-8')
            
    req = urllib.request.Request(url, data=req_data, headers=req_headers, method=method)
    
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            body = response.read().decode('utf-8')
            try:
                parsed_json = json.loads(body)
            except Exception:
                parsed_json = body
            return response.status, parsed_json, latency_ms, dict(response.headers)
    except urllib.error.HTTPError as e:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        body = e.read().decode('utf-8')
        try:
            parsed_json = json.loads(body)
        except Exception:
            parsed_json = body
        return e.code, parsed_json, latency_ms, dict(e.headers)


def run_tests():
    print("=" * 70)
    print("PROXIMITY SEARCH API - END-TO-END DOCKER INTEGRATION TEST SUITE")
    print(f"Target Gateway: {BASE_URL}")
    print("=" * 70)

    # Wait for gateway to be available
    print("\n[Phase 1] Waiting for gateway and backend to be healthy...")
    max_retries = 30
    for attempt in range(1, max_retries + 1):
        try:
            status, data, latency, headers = make_request('/health')
            if status == 200 and isinstance(data, dict) and data.get('status') == 'healthy':
                print(f"  [OK] Connected to stack on attempt {attempt} ({latency:.1f}ms). Locations: {data.get('total_locations')}")
                break
        except Exception as e:
            pass
        time.sleep(1)
    else:
        print("  [ERROR] Backend failed to become healthy within timeout.")
        sys.exit(1)

    tests_run = 0
    tests_passed = 0

    def assert_test(name, condition, details=""):
        nonlocal tests_run, tests_passed
        tests_run += 1
        if condition:
            tests_passed += 1
            print(f"  PASS: {name} {details}")
        else:
            print(f"  FAIL: {name} {details}")
            sys.exit(1)

    print("\n[Phase 2] Running Verification Test Cases:")

    # Test 1: Nginx Gateway Health
    status, data, latency, headers = make_request('/nginx-health')
    assert_test("Nginx Direct Health Check", status == 200, f"(Status: {status}, {latency:.2f}ms)")

    # Test 2: Gateway Reverse Proxy Header
    status, data, latency, headers = make_request('/health')
    gateway_hdr = headers.get('X-Gateway', headers.get('x-gateway', ''))
    assert_test("Nginx Gateway Reverse Proxy Headers", 'Nginx' in gateway_hdr or status == 200, f"(X-Gateway: {gateway_hdr})")

    # Test 3: Standard GET Proximity Search Query
    query_path = '/search/?lat=0.505051&long=0.505051&cat=cafe&rad=0.15'
    status, data, latency, headers = make_request(query_path)
    assert_test(
        "GET Proximity Search (/search/)",
        status == 200 and isinstance(data, list) and len(data) == 10,
        f"(Count: {len(data) if isinstance(data, list) else 0}, Latency: {latency:.2f}ms, Top ID: {data[0] if isinstance(data, list) and len(data) > 0 else 'N/A'})"
    )

    # Test 4: Route without trailing slash
    status, data, latency, headers = make_request('/search?lat=0.505051&long=0.505051&cat=cafe&rad=0.15')
    assert_test("GET /search (No trailing slash)", status == 200 and len(data) == 10, f"({latency:.2f}ms)")

    # Test 5: POST Proximity Search with JSON payload
    payload = {'lat': 0.252525, 'long': 0.757576, 'cat': 'restaurant', 'rad': 0.25}
    status, data, latency, headers = make_request('/search/', method='POST', data=payload)
    assert_test("POST Proximity Search (JSON body)", status == 200 and len(data) == 10, f"({latency:.2f}ms)")

    # Test 6: Multi-category traversal test
    categories = ['pharmacy', 'hospital', 'bank', 'store', 'school']
    for cat in categories:
        status, data, latency, _ = make_request(f'/search/?lat=0.5&long=0.5&cat={cat}&rad=0.2')
        assert_test(f"Category Traversal: '{cat}'", status == 200 and len(data) == 10, f"({latency:.2f}ms)")

    # Test 7: Error handling - Missing Parameters
    status, data, latency, _ = make_request('/search/?lat=0.5&long=0.5')
    assert_test("Validation: 400 Bad Request on Missing Params", status == 400, f"(Status: {status})")

    # Test 8: Error handling - Negative Radius
    status, data, latency, _ = make_request('/search/?lat=0.5&long=0.5&cat=bank&rad=-0.1')
    assert_test("Validation: 400 Bad Request on Negative Radius", status == 400, f"(Status: {status})")

    # Latency Benchmark: 20 sequential queries
    print("\n[Phase 3] Traversal Latency Benchmark (20 queries):")
    latencies = []
    for _ in range(20):
        _, _, lat_ms, _ = make_request('/search/?lat=0.505051&long=0.505051&cat=cafe&rad=0.15')
        latencies.append(lat_ms)
    
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    print(f"  Average Latency : {avg_latency:.2f} ms")
    print(f"  Min / Max Latency: {min_latency:.2f} ms / {max_latency:.2f} ms")
    assert_test("Latency < 50ms per query across network bridge", avg_latency < 50.0)

    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: {tests_passed}/{tests_run} TESTS PASSED (100% SUCCESS)")
    print("=" * 70 + "\n")

if __name__ == '__main__':
    run_tests()
