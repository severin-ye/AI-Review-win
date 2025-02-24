import unittest
from src.core.ai_review import AIReviewer

class TestAIReviewer(unittest.TestCase):
    def setUp(self):
        self.reviewer = AIReviewer()

    def test_review_text(self):
        """测试文本审校功能"""
        test_text = "这是一个测试文本。"
        result = self.reviewer.review_text(test_text)
        self.assertIsNotNone(result)

    def test_batch_review(self):
        """测试批量审校功能"""
        test_texts = ["文本1", "文本2", "文本3"]
        results = self.reviewer.batch_review(test_texts)
        self.assertEqual(len(results), len(test_texts))

if __name__ == '__main__':
    unittest.main() 