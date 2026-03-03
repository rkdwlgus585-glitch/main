import json
import os
import tempfile
import unittest
from unittest.mock import patch

from trend_radar_v2 import TrendRadarV2


class _Resp:
    def __init__(self, status_code=200, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.headers = headers or {}

    def json(self):
        if self._json_data is not None:
            return self._json_data
        return json.loads(self.text)


class TrendRadarV2Test(unittest.TestCase):
    def test_similarity_prefers_identical_keywords(self):
        radar = TrendRadarV2()
        score = radar._similarity("construction license registration", "construction license registration")
        self.assertGreaterEqual(score, 0.99)

    def test_is_duplicate_detects_similar_existing_title(self):
        radar = TrendRadarV2()
        radar.existing_posts = [{"title": "construction license registration guide 2026", "source": "wordpress"}]

        is_dup, reason, sim = radar._is_duplicate("construction license registration process", threshold=0.4)

        self.assertTrue(is_dup)
        self.assertGreaterEqual(sim, 0.4)
        self.assertTrue(reason)

    def test_generate_search_seeds_is_day_stable(self):
        radar = TrendRadarV2()
        seeds1 = radar._generate_search_seeds(count=20)
        seeds2 = radar._generate_search_seeds(count=20)
        self.assertEqual(seeds1, seeds2)
        self.assertTrue(seeds1)

    def test_get_google_uses_https_endpoint(self):
        radar = TrendRadarV2()
        with patch("trend_radar_v2.requests.get") as mget:
            mget.return_value = _Resp(status_code=200, text='["q", ["a", "b"]]')
            out = radar._get_google("construction")

        self.assertEqual(out, ["a", "b"])
        called_url = mget.call_args.args[0]
        self.assertTrue(called_url.startswith("https://"))

    def test_fetch_existing_posts_uses_auth_headers_when_present(self):
        radar = TrendRadarV2(wp_headers={"Authorization": "Bearer token"})
        radar.history = {"keywords": [], "topics": {}}

        with tempfile.TemporaryDirectory() as td:
            radar.CACHE_FILE = os.path.join(td, "wp_posts_cache.json")
            rows = [
                {
                    "id": 10,
                    "title": {"rendered": "construction license process"},
                    "slug": "new-license",
                    "status": "publish",
                }
            ]
            with patch("trend_radar_v2.requests.get") as mget:
                mget.return_value = _Resp(status_code=200, json_data=rows, headers={"X-WP-TotalPages": "1"})
                posts = radar._fetch_existing_posts({"WP_URL": "https://example.com/wp-json/wp/v2"})

        self.assertTrue(any(p.get("source") == "wordpress" for p in posts))
        self.assertEqual(mget.call_args.kwargs.get("headers"), {"Authorization": "Bearer token"})


if __name__ == "__main__":
    unittest.main()
