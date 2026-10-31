"""检查包能否导入，以及配置路径是否指向本仓库。"""

import unittest

import paper_trail
from paper_trail import (
    chunking,
    config,
    corpus,
    generation,
    indexing,
    parsing,
    retrieval,
    verification,
)


class SkeletonTest(unittest.TestCase):
    def test_packages_import(self):
        """导入主包和 7 个子包。"""
        modules = [
            paper_trail,
            corpus,
            parsing,
            chunking,
            indexing,
            retrieval,
            generation,
            verification,
        ]
        for module in modules:
            self.assertIsNotNone(module)

    def test_paths_point_at_this_repo(self):
        """版本号为 0.0.0，项目根目录和 manifest 路径正确。"""
        self.assertEqual(paper_trail.__version__, "0.0.0")
        self.assertTrue((config.PROJECT_ROOT / "pyproject.toml").is_file())
        self.assertEqual(config.MANIFEST_PATH, config.DATA_DIR / "manifest.json")
        self.assertEqual(config.RAW_PDF_DIR, config.DATA_DIR / "raw_pdf")
        self.assertEqual(config.PARSED_DIR, config.DATA_DIR / "parsed")
        self.assertTrue(config.MANIFEST_PATH.is_file())


if __name__ == "__main__":
    unittest.main()
