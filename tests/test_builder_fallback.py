import unittest

from app import resolve_component_image_path


class BuilderFallbackTests(unittest.TestCase):
    def test_missing_image_path_uses_placeholder(self):
        self.assertEqual(
            resolve_component_image_path("/does/not/exist.png"),
            "/static/images/placeholder.svg"
        )


if __name__ == "__main__":
    unittest.main()
