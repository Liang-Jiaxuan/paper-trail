"""检查 data/manifest.json 的字段和引用是否自洽，不核实论文元数据。"""

import json
import unittest

from paper_trail import config

PAPER_FIELDS = {
    "paper_id",
    "title",
    "authors",
    "year",
    "venue",
    "arxiv_id",
    "arxiv_version",
    "doi",
    "source_url",
    "license",
    "layout",
    "topics",
    "status",
    "metadata_verified",
    "sha256",
    "retrieved_at",
}
STATUSES = {"candidate", "selected", "excluded"}


class ManifestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """读取清单一次，供各项测试共用。"""
        with open(config.MANIFEST_PATH, encoding="utf-8") as f:
            cls.manifest = json.load(f)

    def test_schema_version(self):
        """清单版本必须是 1。"""
        self.assertEqual(self.manifest["schema_version"], 1)

    def test_papers_have_all_fields(self):
        """每篇论文字段齐全，status 合法，topics 非空。"""
        for paper in self.manifest["papers"]:
            with self.subTest(paper=paper["paper_id"]):
                self.assertEqual(set(paper), PAPER_FIELDS)
                self.assertIn(paper["status"], STATUSES)
                self.assertTrue(paper["topics"])

    def test_paper_ids_are_unique(self):
        """paper_id 不重复。"""
        ids = [p["paper_id"] for p in self.manifest["papers"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_collections_reference_known_papers(self):
        """文集引用的 paper_id 都在 papers 中。"""
        known = {p["paper_id"] for p in self.manifest["papers"]}
        for collection in self.manifest["collections"]:
            with self.subTest(collection=collection["collection_id"]):
                self.assertLessEqual(set(collection["paper_ids"]), known)


if __name__ == "__main__":
    unittest.main()
