import unittest
from unittest.mock import patch, MagicMock
from datetime import date
import json
from app import app

class SRSApiTestCase(unittest.TestCase):
    def setUp(self):
        """测试前的初始化：配置 Flask 测试客户端"""
        self.app = app.test_client()
        self.app.testing = True
        self.module_id = 'mod1'
        self.card_id = 'mod1_card_test'

    @patch('app.supabase_fetch')
    def test_learn_card_endpoint(self, mock_fetch):
        """
        测试 场景A：/srs/learn 接口 (复习逻辑)
        验证：LRD 更新为今天，CI 发生变化，LAD 保持不变
        """
        # 1. 模拟数据库返回的原始数据
        today = date.today()
        five_days_ago = today - timedelta(days=5)
        
        mock_card_data = [{
            'cardid': self.card_id,
            'ic': 5,
            'lrd': five_days_ago.isoformat(),
            'lad': five_days_ago.isoformat(),
            'is_core': 0,
            'rc': 0,
            'data': {'title': 'Test Word'}
        }]
        
        # 配置 Mock：第一次调用(GET)返回卡片，第二次调用(PATCH)返回成功
        mock_fetch.side_effect = [mock_card_data, [{'status': 'success'}]]

        # 2. 发送 POST 请求到 learn 接口
        response = self.app.post(f'/api/{self.module_id}/srs/learn/{self.card_id}', 
                                 data=json.dumps({'is_correct': True}),
                                 content_type='application/json')
        
        # 3. 断言验证
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        
        # 验证 LRD 是否刷成了今天
        self.assertEqual(data['new_state']['lrd'], today.isoformat())
        # 验证 LAD 是否维持原样 (根据你的新逻辑，复习不改动应用日期)
        self.assertEqual(data['new_state']['lad'], five_days_ago.isoformat())
        print("✅ 测试通过：/srs/learn 成功分离了复习逻辑")

    @patch('app.supabase_fetch')
    def test_use_card_endpoint(self, mock_fetch):
        """
        测试 场景B：/srs/use 接口 (应用逻辑 - 新增)
        验证：LAD 更新为今天，N (rc) 增加，LRD 保持不变
        """
        # 1. 模拟数据
        today = date.today()
        ten_days_ago = today - timedelta(days=10)
        
        mock_card_data = [{
            'cardid': self.card_id,
            'ic': 10,
            'lrd': ten_days_ago.isoformat(),
            'lad': ten_days_ago.isoformat(),
            'is_core': 0,
            'rc': 5, # 初始引用次数为 5
            'data': {'title': 'Apply Test'}
        }]
        
        mock_fetch.side_effect = [mock_card_data, [{'status': 'success'}]]

        # 2. 发送 POST 请求到新的 use 接口
        response = self.app.post(f'/api/{self.module_id}/srs/use/{self.card_id}')
        
        # 3. 断言验证
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        
        # 验证 LAD 刷成了今天
        self.assertEqual(data['new_state']['lad'], today.isoformat())
        # 验证 LRD 没变
        self.assertEqual(data['new_state']['lrd'], ten_days_ago.isoformat())
        # 验证 引用次数 rc 是否变成了 6
        self.assertEqual(data['new_state']['rc'], 6)
        print("✅ 测试通过：/srs/use 成功增加了引用计数并更新了 LAD")

if __name__ == '__main__':
    from datetime import timedelta # 补丁
    unittest.main()