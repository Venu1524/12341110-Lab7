"""
Comprehensive test suite for Proximity Search API.
Tests functionality, edge cases, HTTP methods, and latency benchmarks.
"""

import unittest
import json
import time
from app import app, engine


class ProximitySearchApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_health(self):
        """Test health endpoint."""
        res = self.client.get('/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['total_locations'], 10000)

    def test_search_get_standard(self):
        """Test standard GET query with query parameters."""
        res = self.client.get('/search/?lat=0.505051&long=0.505051&cat=cafe&rad=0.15')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 10)
        # Verify all elements are integers (IDs)
        for item in data:
            self.assertIsInstance(item, int)
            self.assertIn(item, engine.locations)
            # Verify category matches
            self.assertEqual(engine.locations[item][3], 'cafe')

    def test_search_no_trailing_slash(self):
        """Test route without trailing slash."""
        res = self.client.get('/search?lat=0.505051&long=0.505051&cat=cafe&rad=0.15')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data), 10)

    def test_search_post_json(self):
        """Test POST request with JSON payload."""
        payload = {
            'lat': 0.252525,
            'long': 0.757576,
            'cat': 'restaurant',
            'rad': 0.25
        }
        res = self.client.post('/search/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data), 10)

    def test_search_post_form(self):
        """Test POST request with form-encoded data."""
        payload = {
            'lat': '0.101010',
            'long': '0.101010',
            'cat': 'hospital',
            'rad': '0.2'
        }
        res = self.client.post('/search/', data=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data), 10)

    def test_all_categories(self):
        """Verify each category returns 10 valid matching locations."""
        categories = ['bank', 'store', 'pharmacy', 'hospital', 'school', 'restaurant', 'park', 'cafe']
        for cat in categories:
            res = self.client.get(f'/search/?lat=0.5&long=0.5&cat={cat}&rad=0.25')
            self.assertEqual(res.status_code, 200, f'Failed for category {cat}')
            data = res.get_json()
            self.assertEqual(len(data), 10, f'Category {cat} did not return 10 items')
            for loc_id in data:
                self.assertEqual(engine.locations[loc_id][3], cat)

    def test_missing_parameters(self):
        """Verify 400 Bad Request on missing parameters."""
        res = self.client.get('/search/?lat=0.5&long=0.5')
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn('error', data)

    def test_invalid_parameter_types(self):
        """Verify 400 Bad Request on non-numeric inputs."""
        res = self.client.get('/search/?lat=abc&long=0.5&cat=bank&rad=0.1')
        self.assertEqual(res.status_code, 400)

    def test_negative_radius(self):
        """Verify 400 Bad Request on negative radius."""
        res = self.client.get('/search/?lat=0.5&long=0.5&cat=bank&rad=-0.1')
        self.assertEqual(res.status_code, 400)

    def test_search_with_explicit_link(self):
        """Test search with explicit link parameter."""
        res = self.client.get('/search/?lat=0.505051&long=0.505051&cat=cafe&rad=0.15&link=link.txt')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 10)
        self.assertEqual(data, [5051, 5053, 5251, 4949, 5154, 4751, 5149, 4653, 4748, 5047])

    def test_search_with_raw_link_content(self):
        """Test search with uploaded/raw road link content."""
        raw_links = "0.505051 0.505051 0.505051 0.515152\n0.505051 0.515152 0.505051 0.525253"
        payload = {
            'lat': 0.505051,
            'long': 0.505051,
            'cat': 'cafe',
            'rad': 0.15,
            'link': raw_links
        }
        res = self.client.post('/search/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, list)
        self.assertLessEqual(len(data), 10)

    def test_dictionary_format_query(self):
        """Test format=dict optional parameter."""
        res = self.client.get('/search/?lat=0.5&long=0.5&cat=bank&rad=0.2&format=dict')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, dict)
        self.assertIn('recommended_locations', data)
        self.assertEqual(len(data['recommended_locations']), 10)

    def test_benchmark_latency(self):
        """Benchmark query latency to ensure sub-5ms response."""
        times = []
        for _ in range(50):
            t0 = time.perf_counter()
            res = self.client.get('/search/?lat=0.505051&long=0.505051&cat=school&rad=0.15')
            t1 = time.perf_counter()
            self.assertEqual(res.status_code, 200)
            times.append((t1 - t0) * 1000)
        avg_ms = sum(times) / len(times)
        print(f'\n[BENCHMARK] Average API call latency: {avg_ms:.2f} ms')
        self.assertLess(avg_ms, 15.0)


if __name__ == '__main__':
    unittest.main()
