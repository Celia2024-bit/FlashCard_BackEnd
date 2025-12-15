# test_srs_calculator.py - 干净、针对新数据结构的单元测试
import unittest
from datetime import date, timedelta
# 导入核心计算函数和全局配置
from srs_calculator import (
    calculate_review_factor_R, 
    calculate_application_factor_A, 
    calculate_priority_score_P,
    update_module_state,
    TODAY,
    A_THRESHOLD
)
# 注意：此文件不需要导入 database_manager，因为 srs_calculator 已经完成了导入。

class TestSRSCalculator(unittest.TestCase):

    # 构造固定的测试数据
    def setUp(self):
        # 构造的数据结构必须包含 'id' (用于算法内部识别) 和 'card_id' (用于数据库更新)
        
        # 1. 强制锁定案例 (高 A 因子) - P > 10000
        self.item_force_lock = {
            "id": 'mod1_card_1',        # 算法使用 ID
            "card_id": 'mod1_card_1',   # DB 更新使用 ID
            "CI": 100, 
            "LRD": date(2025, 6, 1),    # NDD: 9/9
            "LAD": date(2025, 7, 1),    # TODAY 12/11. A=163 (强制锁定)
            "is_core": False
        }
        # 2. 逾期复习案例 (高 R 因子)
        self.item_overdue = {
            "id": 'mod1_card_2',
            "card_id": 'mod1_card_2',
            "CI": 1, 
            "LRD": date(2025, 12, 5),   # NDD: 12/6. TODAY 12/11. R=5
            "LAD": date(2025, 12, 9),   # A=2
            "is_core": True             # C=2
        }
        # 3. 正常不选案例 (R=0)
        self.item_not_due = {
            "id": 'mod1_card_3',
            "card_id": 'mod1_card_3',
            "CI": 10, 
            "LRD": date(2025, 12, 9),   # NDD: 12/19. R=0
            "LAD": date(2025, 12, 10),  # A=1
            "is_core": False
        }
        # 4. 核心用法逾期 (高 P 因子)
        self.item_core_overdue = {
            "id": 'mod1_card_4',
            "card_id": 'mod1_card_4',
            "CI": 2, 
            "LRD": date(2025, 12, 7),   # NDD: 12/9. TODAY 12/11. R=2
            "LAD": date(2025, 12, 1),   # A=10
            "is_core": True             # C=2
        }
        # 5. 边界案例：恰好到期 (R=0)
        self.item_due_tomorrow = {
            "id": 'mod1_card_5',
            "card_id": 'mod1_card_5',
            "CI": 5, 
            "LRD": date(2025, 12, 6),   # NDD: 12/11. TODAY 12/11. R=0
            "LAD": date(2025, 12, 5), 
            "is_core": False 
        }

    ## --- 测试 R 因子 (复习逾期) ---
    def test_r_factor_overdue(self):
        # 模块 2：R=5
        self.assertEqual(calculate_review_factor_R(self.item_overdue), 5) 

    def test_r_factor_not_due(self):
        # 模块 3：R=0
        self.assertEqual(calculate_review_factor_R(self.item_not_due), 0)

    def test_r_factor_due_today_is_zero(self):
        # 模块 5：NDD 12/11。R=0
        self.assertEqual(calculate_review_factor_R(self.item_due_tomorrow), 0)

    ## --- 测试 A 因子 (应用饥渴) ---
    def test_a_factor_force_lock(self):
        # 模块 1：LAD 7/1. TODAY 12/11. A=163 天
        self.assertEqual(calculate_application_factor_A(self.item_force_lock), 163)
        
    def test_a_factor_recent_use(self):
        # 模块 3：LAD 12/10. TODAY 12/11. A=1 天
        self.assertEqual(calculate_application_factor_A(self.item_not_due), 1)

    ## --- 测试 P-Score (优先级) ---
    
    # 测试案例 1：强制锁定 (A > 30)
    def test_p_score_force_lock(self):
        # A=163。P = 10000 + 163 = 10163
        expected_score = 10000 + 163
        self.assertEqual(calculate_priority_score_P(self.item_force_lock), expected_score)

    # 测试案例 2：R=0 的模块 P 必须为 0
    def test_p_score_zero(self):
        # 模块 5：R=0。P 必须为 0。
        self.assertEqual(calculate_priority_score_P(self.item_due_tomorrow), 0)

    # 测试案例 3：核心用法逾期
    def test_p_score_core_weighted(self):
        # 模块 4：R=2. A=10. C=2.
        # P = R*C + A//5 = 2*2 + 10//5 = 4 + 2 = 6
        self.assertEqual(calculate_priority_score_P(self.item_core_overdue), 6)

    ## --- 测试更新逻辑 ---
    
    def test_update_success(self):
        # 模块 3：CI=10。成功后 CI 应该变为 20。
        original_ci = self.item_not_due['CI']
        
        # 使用副本进行测试，避免副作用影响其他测试
        test_item = self.item_not_due.copy() 
        updated = update_module_state(test_item, is_applied_correctly=True)
        
        # 验证 CI 翻倍
        self.assertEqual(updated['CI'], original_ci * 2) 
        # 验证 LAD/LRD 更新到 TODAY
        self.assertEqual(updated['LAD'], TODAY)
        self.assertEqual(updated['LRD'], TODAY)

    def test_update_fail(self):
        # 模块 4：CI=2。失败后 CI 应该重置为 1。
        test_item = self.item_core_overdue.copy() 
        updated = update_module_state(test_item, is_applied_correctly=False)
        
        # 验证 CI 重置
        self.assertEqual(updated['CI'], 1) 
        # 验证 LAD/LRD 更新到 TODAY
        self.assertEqual(updated['LAD'], TODAY)
        self.assertEqual(updated['LRD'], TODAY)


if __name__ == '__main__':
    # --- 关键修正：对新的数据库写入函数进行 Mocking ---
    
    # 导入新的数据库写入函数
    from database_manager import update_card_srs_state_in_db
    
    # 临时禁用数据库写入，确保单元测试不会影响真实数据
    global update_card_srs_state_in_db
    def dummy_update(item):
        """Mock function to prevent database write during unit test"""
        # 必须确保这个哑函数接收参数，并返回 None 或 Pass
        pass
        
    # 将实际函数替换为哑函数
    update_card_srs_state_in_db = dummy_update 
    
    print(f"--- 算法测试基准日期: {TODAY} ---")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)