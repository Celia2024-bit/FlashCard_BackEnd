# test_add_card_handler.py - 针对 add_card_handler.py 的单元测试
import unittest
import json
import os
import sqlite3
import tempfile
import shutil
from datetime import date, timedelta
from unittest.mock import patch

# 导入模块而不是直接导入函数，避免触发 __main__ 代码
import add_card_handler


class TestAddCardHandler(unittest.TestCase):
    """测试卡片添加、删除、更新功能"""

    @classmethod
    def setUpClass(cls):
        """在所有测试前创建临时目录和文件"""
        # 创建临时目录
        cls.test_dir = tempfile.mkdtemp()
        cls.test_db = os.path.join(cls.test_dir, 'test_srs_data.db')
        cls.test_json = os.path.join(cls.test_dir, 'test_mod1_cards.json')
        
        print(f"\n🔧 测试环境:")
        print(f"   临时目录: {cls.test_dir}")
        print(f"   测试数据库: {cls.test_db}")
        print(f"   测试JSON: {cls.test_json}")

    @classmethod
    def tearDownClass(cls):
        """在所有测试后清理临时文件"""
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)
            print(f"\n🧹 已清理临时目录: {cls.test_dir}")

    def setUp(self):
        """每个测试前的准备工作"""
        # 创建测试数据库
        self._create_test_database()
        
        # 创建测试 JSON 文件（初始为空）
        with open(self.test_json, 'w', encoding='utf-8') as f:
            json.dump([], f)
        
        # Mock 数据库和文件路径
        # 注意：需要同时 Mock add_card_handler 和 database_manager 中的 DB_NAME
        self.db_patcher1 = patch('add_card_handler.DB_NAME', self.test_db)
        self.db_patcher2 = patch('database_manager.DB_NAME', self.test_db)
        self.json_patcher = patch('add_card_handler.CARDS_JSON_FILE', self.test_json)
        
        self.db_patcher1.start()
        self.db_patcher2.start()
        self.json_patcher.start()

    def tearDown(self):
        """每个测试后的清理工作"""
        self.db_patcher1.stop()
        self.db_patcher2.stop()
        self.json_patcher.stop()
        
        # 清理测试文件
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists(self.test_json):
            os.remove(self.test_json)

    def _create_test_database(self):
        """创建测试数据库表"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                card_id TEXT PRIMARY KEY,
                module_id TEXT NOT NULL,
                key_title TEXT,
                ci INTEGER NOT NULL,
                lrd TEXT NOT NULL,
                lad TEXT NOT NULL,
                is_core INTEGER NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()

    def _get_card_from_db(self, card_id):
        """从数据库获取卡片"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cards WHERE card_id = ?', (card_id,))
        result = cursor.fetchone()
        conn.close()
        return result

    def _get_cards_from_json(self):
        """从 JSON 文件获取所有卡片"""
        with open(self.test_json, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ========== 测试添加卡片 ==========

    def test_add_card_success_full_data(self):
        """测试 1: 添加完整数据的卡片"""
        card_data = {
            'cardId': 'mod1_card_100',
            'title': 'Test Expression',
            'Original': 'Original text here',
            'Tone': 'formal',
            'Explain': 'This is an explanation',
            'Usage': 'Usage example',
            'Extended': 'Extended info',
            'Mysentence': 'My test sentence',
            'Corrected': 'Corrected sentence',
            'ExplainCorrected': 'Correction explanation',
            'Fluency': '2'
        }
        
        result = add_card_handler.add_new_card(card_data)
        
        # 验证返回值
        self.assertTrue(result, "添加应该成功")
        
        # 验证数据库
        db_card = self._get_card_from_db('mod1_card_100')
        self.assertIsNotNone(db_card, "数据库中应该有这张卡片")
        self.assertEqual(db_card[0], 'mod1_card_100', "card_id 正确")
        self.assertEqual(db_card[1], 'mod1', "module_id 正确")
        self.assertEqual(db_card[2], 'Test Expression', "标题正确")
        
        # 验证 JSON 文件
        json_cards = self._get_cards_from_json()
        self.assertEqual(len(json_cards), 1, "JSON 中应该有 1 张卡片")
        self.assertEqual(json_cards[0]['cardId'], 'mod1_card_100')
        self.assertEqual(json_cards[0]['title'], 'Test Expression')
        self.assertEqual(json_cards[0]['Tone'], 'formal')

    def test_add_card_success_minimal_data(self):
        """测试 2: 添加最小数据的卡片（仅必填字段）"""
        card_data = {
            'cardId': 'mod1_card_101',
            'title': 'Minimal Test Card'
        }
        
        result = add_card_handler.add_new_card(card_data)
        
        self.assertTrue(result, "添加应该成功")
        
        # 验证默认值
        json_cards = self._get_cards_from_json()
        card = json_cards[0]
        
        self.assertEqual(card['title'], 'Minimal Test Card')
        self.assertEqual(card['Tone'], 'informal', "应该有默认 Tone")
        self.assertEqual(card['Fluency'], '1', "应该有默认 Fluency")
        self.assertEqual(card['Original'], '', "应该有空的 Original")

    def test_add_card_fail_missing_cardId(self):
        """测试 3: 缺少 cardId 应该失败"""
        card_data = {
            'title': 'No ID Card'
        }
        
        result = add_card_handler.add_new_card(card_data)
        
        self.assertFalse(result, "缺少 cardId 应该失败")
        
        # 验证数据库和 JSON 都没有添加
        json_cards = self._get_cards_from_json()
        self.assertEqual(len(json_cards), 0, "JSON 中不应该有卡片")

    def test_add_card_fail_missing_title(self):
        """测试 4: 缺少 title 应该失败"""
        card_data = {
            'cardId': 'mod1_card_102'
        }
        
        result = add_card_handler.add_new_card(card_data)
        
        self.assertFalse(result, "缺少 title 应该失败")

    def test_add_card_fail_duplicate_id(self):
        """测试 5: 重复的 cardId 应该失败"""
        card_data = {
            'cardId': 'mod1_card_103',
            'title': 'First Card'
        }
        
        # 第一次添加
        result1 = add_card_handler.add_new_card(card_data)
        self.assertTrue(result1, "第一次添加应该成功")
        
        # 尝试添加相同 ID
        card_data2 = {
            'cardId': 'mod1_card_103',
            'title': 'Second Card'
        }
        
        result2 = add_card_handler.add_new_card(card_data2)
        self.assertFalse(result2, "重复 ID 应该失败")
        
        # 验证只有一张卡片
        json_cards = self._get_cards_from_json()
        self.assertEqual(len(json_cards), 1, "应该只有 1 张卡片")
        self.assertEqual(json_cards[0]['title'], 'First Card', "应该保留第一张卡片")

    def test_add_card_srs_initial_state(self):
        """测试 6: 验证初始 SRS 状态"""
        card_data = {
            'cardId': 'mod1_card_104',
            'title': 'SRS Test Card'
        }
        
        with patch('add_card_handler.TODAY', date(2025, 12, 15)):
            result = add_card_handler.add_new_card(card_data)
        
        self.assertTrue(result)
        
        # 验证 SRS 状态
        db_card = self._get_card_from_db('mod1_card_104')
        ci = db_card[3]  # CI
        lrd = db_card[4]  # LRD
        lad = db_card[5]  # LAD
        is_core = db_card[6]  # is_core
        
        self.assertEqual(ci, 5, "初始 CI 应该是 5")
        self.assertEqual(lrd, '2025-12-10', "LRD 应该是 TODAY - 5 天")
        self.assertEqual(lad, '2025-12-14', "LAD 应该是 TODAY - 1 天")
        self.assertEqual(is_core, 0, "初始 is_core 应该是 0")

    # ========== 测试删除卡片 ==========

    def test_delete_card_success(self):
        """测试 7: 成功删除卡片"""
        # 先添加卡片
        add_card_handler.add_new_card({
            'cardId': 'mod1_card_200',
            'title': 'To Be Deleted'
        })
        
        # 验证卡片存在
        self.assertIsNotNone(self._get_card_from_db('mod1_card_200'))
        self.assertEqual(len(self._get_cards_from_json()), 1)
        
        # 删除卡片
        result = add_card_handler.delete_card('mod1_card_200')
        
        self.assertTrue(result, "删除应该成功")
        
        # 验证卡片已删除
        self.assertIsNone(self._get_card_from_db('mod1_card_200'))
        self.assertEqual(len(self._get_cards_from_json()), 0)

    def test_delete_card_fail_not_found(self):
        """测试 8: 删除不存在的卡片应该失败"""
        result = add_card_handler.delete_card('nonexistent_card')
        
        self.assertFalse(result, "删除不存在的卡片应该失败")

    def test_delete_card_from_multiple(self):
        """测试 9: 从多张卡片中删除一张"""
        # 添加多张卡片
        add_card_handler.add_new_card({'cardId': 'mod1_card_201', 'title': 'Card 1'})
        add_card_handler.add_new_card({'cardId': 'mod1_card_202', 'title': 'Card 2'})
        add_card_handler.add_new_card({'cardId': 'mod1_card_203', 'title': 'Card 3'})
        
        self.assertEqual(len(self._get_cards_from_json()), 3)
        
        # 删除中间的卡片
        result = add_card_handler.delete_card('mod1_card_202')
        
        self.assertTrue(result)
        
        # 验证
        json_cards = self._get_cards_from_json()
        self.assertEqual(len(json_cards), 2, "应该剩余 2 张卡片")
        
        card_ids = [c['cardId'] for c in json_cards]
        self.assertNotIn('mod1_card_202', card_ids)
        self.assertIn('mod1_card_201', card_ids)
        self.assertIn('mod1_card_203', card_ids)

    # ========== 测试更新卡片 ==========

    def test_update_card_success(self):
        """测试 10: 成功更新卡片"""
        # 先添加卡片
        add_card_handler.add_new_card({
            'cardId': 'mod1_card_300',
            'title': 'Original Title',
            'Explain': 'Original Explanation',
            'Tone': 'informal'
        })
        
        # 更新卡片
        result = add_card_handler.update_card('mod1_card_300', {
            'title': 'Updated Title',
            'Explain': 'Updated Explanation'
        })
        
        self.assertTrue(result, "更新应该成功")
        
        # 验证数据库中的标题
        db_card = self._get_card_from_db('mod1_card_300')
        self.assertEqual(db_card[2], 'Updated Title', "数据库中的标题应该更新")
        
        # 验证 JSON 文件
        json_cards = self._get_cards_from_json()
        card = json_cards[0]
        
        self.assertEqual(card['title'], 'Updated Title')
        self.assertEqual(card['Explain'], 'Updated Explanation')
        self.assertEqual(card['Tone'], 'informal', "未更新的字段应该保持不变")

    def test_update_card_fail_not_found(self):
        """测试 11: 更新不存在的卡片应该失败"""
        result = add_card_handler.update_card('nonexistent_card', {
            'title': 'New Title'
        })
        
        self.assertFalse(result, "更新不存在的卡片应该失败")

    def test_update_card_partial_fields(self):
        """测试 12: 部分字段更新"""
        # 添加卡片
        add_card_handler.add_new_card({
            'cardId': 'mod1_card_301',
            'title': 'Original Title',
            'Explain': 'Original Explanation',
            'Usage': 'Original Usage',
            'Tone': 'formal'
        })
        
        # 只更新 Usage 字段
        result = add_card_handler.update_card('mod1_card_301', {
            'Usage': 'Updated Usage'
        })
        
        self.assertTrue(result)
        
        # 验证
        json_cards = self._get_cards_from_json()
        card = json_cards[0]
        
        self.assertEqual(card['Usage'], 'Updated Usage', "Usage 应该更新")
        self.assertEqual(card['title'], 'Original Title', "title 应该不变")
        self.assertEqual(card['Explain'], 'Original Explanation', "Explain 应该不变")

    def test_update_card_without_title(self):
        """测试 13: 更新非标题字段不应影响数据库"""
        # 添加卡片
        add_card_handler.add_new_card({
            'cardId': 'mod1_card_302',
            'title': 'Original Title',
            'Explain': 'Original'
        })
        
        # 只更新 Explain（不包含 title）
        result = add_card_handler.update_card('mod1_card_302', {
            'Explain': 'Updated Explanation'
        })
        
        self.assertTrue(result)
        
        # 验证数据库标题未变
        db_card = self._get_card_from_db('mod1_card_302')
        self.assertEqual(db_card[2], 'Original Title')
        
        # 验证 JSON 中 Explain 已更新
        json_cards = self._get_cards_from_json()
        self.assertEqual(json_cards[0]['Explain'], 'Updated Explanation')

    # ========== 集成测试 ==========

    def test_full_lifecycle(self):
        """测试 14: 完整生命周期（添加 → 更新 → 删除）"""
        # 1. 添加
        add_result = add_card_handler.add_new_card({
            'cardId': 'mod1_card_400',
            'title': 'Lifecycle Test',
            'Explain': 'Initial'
        })
        self.assertTrue(add_result)
        
        # 验证添加
        self.assertIsNotNone(self._get_card_from_db('mod1_card_400'))
        self.assertEqual(len(self._get_cards_from_json()), 1)
        
        # 2. 更新
        update_result = add_card_handler.update_card('mod1_card_400', {
            'Explain': 'Updated'
        })
        self.assertTrue(update_result)
        
        # 验证更新
        json_cards = self._get_cards_from_json()
        self.assertEqual(json_cards[0]['Explain'], 'Updated')
        
        # 3. 删除
        delete_result = add_card_handler.delete_card('mod1_card_400')
        self.assertTrue(delete_result)
        
        # 验证删除
        self.assertIsNone(self._get_card_from_db('mod1_card_400'))
        self.assertEqual(len(self._get_cards_from_json()), 0)

    def test_multiple_operations(self):
        """测试 15: 多次操作"""
        # 添加多张卡片
        for i in range(1, 6):
            add_card_handler.add_new_card({
                'cardId': f'mod1_card_50{i}',
                'title': f'Card {i}'
            })
        
        # 验证
        self.assertEqual(len(self._get_cards_from_json()), 5)
        
        # 更新部分卡片
        add_card_handler.update_card('mod1_card_502', {'title': 'Updated Card 2'})
        add_card_handler.update_card('mod1_card_504', {'title': 'Updated Card 4'})
        
        # 删除部分卡片
        add_card_handler.delete_card('mod1_card_501')
        add_card_handler.delete_card('mod1_card_503')
        
        # 验证最终状态
        json_cards = self._get_cards_from_json()
        self.assertEqual(len(json_cards), 3, "应该剩余 3 张卡片")
        
        # 验证更新
        card_502 = next(c for c in json_cards if c['cardId'] == 'mod1_card_502')
        self.assertEqual(card_502['title'], 'Updated Card 2')


def run_tests_with_summary():
    """运行测试并显示详细摘要"""
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAddCardHandler)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印摘要
    print("\n" + "="*70)
    print("📊 测试摘要")
    print("="*70)
    print(f"✅ 通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ 失败: {len(result.failures)}")
    print(f"💥 错误: {len(result.errors)}")
    print(f"📝 总计: {result.testsRun}")
    print("="*70)
    
    if result.wasSuccessful():
        print("🎉 所有测试通过！")
    else:
        print("⚠️  有测试失败，请检查上面的详细信息")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests_with_summary()
    exit(0 if success else 1)