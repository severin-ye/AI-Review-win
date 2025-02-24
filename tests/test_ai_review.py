import unittest
from unittest.mock import patch
from src.core.ai_review import AIReviewer

class TestAIReviewer(unittest.TestCase):
    def setUp(self):
        self.reviewer = AIReviewer()

    @patch('src.utils.ai_utils.ai_answer')
    def test_review_text(self, mock_ai_answer):
        """测试文本审校功能"""
        # 设置模拟返回值
        mock_ai_answer.return_value = "这是审校后的文本。"
        
        test_text = "这是一个测试文本。"
        result = self.reviewer.review_text(test_text)
        
        self.assertIsNotNone(result)
        self.assertEqual(result, "这是审校后的文本。")
        mock_ai_answer.assert_called_once_with(test_text)

    @patch('src.utils.ai_utils.ai_answer')
    def test_batch_review(self, mock_ai_answer):
        """测试批量审校功能"""
        # 设置模拟返回值
        mock_ai_answer.side_effect = ["审校结果1", "审校结果2", "审校结果3"]
        
        test_texts = ["文本1", "文本2", "文本3"]
        results = self.reviewer.batch_review(test_texts)
        
        self.assertEqual(len(results), len(test_texts))
        self.assertEqual(results, ["审校结果1", "审校结果2", "审校结果3"])
        self.assertEqual(mock_ai_answer.call_count, 3)

if __name__ == '__main__':
    unittest.main() 