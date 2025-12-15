import sys
from datetime import date, timedelta
# 假设 database_manager.py 在同一目录
from database_manager import get_all_cards_srs_state, update_card_srs_state_in_db

# --- 配置 ---
# 注意：我们将 TODAY 设置为 12月11日，与数据库导入基准日保持一致
TODAY = date(2025, 12, 11) 
A_THRESHOLD = 30 
K_TARGET = 5 # 每日必用模块目标数量

def calculate_review_factor_R(item):
    """
    计算复习需求因子 R：逾期天数。R = max(0, 今天 - (上次复习日 + 间隔))
    """
    next_due_date = item['LRD'] + timedelta(days=item['CI'])
    overdue_days = (TODAY - next_due_date).days
    return max(0, overdue_days)

def calculate_application_factor_A(item):
    """
    计算应用饥渴因子 A：自上次使用以来的天数。A = 今天 - 上次应用日
    """
    days_since_applied = (TODAY - item['LAD']).days
    return days_since_applied

def calculate_priority_score_P(item):
    """
    计算优先级分数 P。
    P-Score = R * C + A // 5 (未锁定)
    P-Score = 10000 + A (强制锁定)
    """
    A = calculate_application_factor_A(item)
    R = calculate_review_factor_R(item)
    C = 2 if item['is_core'] else 1 
    
    # 强制锁定判断
    if A > A_THRESHOLD:
        return 10000 + A # 确保它每天都被选中

    # 优先级填补判断
    if R == 0:
        return 0 # 未到复习日期
    
    # P = R * C + A/5 
    P = R * C + (A // 5) 
    
    return P

def update_module_state(item, is_applied_correctly):
    """
    根据应用结果更新模块的状态 (CI, LRD, LAD)，并写回数据库。
    """
    # 1. 更新 LAD: 消除强制锁定的风险
    item['LAD'] = TODAY 

    # 2. 更新 CI (间隔)
    if is_applied_correctly:
        item['CI'] *= 2 # 成功奖励：间隔翻倍
        print(f"✅ 模块 {item['id']} 应用成功！间隔增至 {item['CI']} 天。")
    else:
        item['CI'] = 1 # 失败惩罚：间隔重置
        print(f"❌ 模块 {item['id']} 应用错误！间隔重置为 1 天。")

    # 3. 更新 LRD
    item['LRD'] = TODAY
    
    # 4. 持久化到数据库
    update_card_srs_state_in_db(item) # <-- 替换为新的函数名
    
    return item

def generate_must_use_list():
    """
    生成“今日必用”清单 (K_TARGET=5)
    """
    # 从数据库读取所有数据
    DATABASE = get_all_cards_srs_state()
    
    k_force = []
    candidates = []

    for item in DATABASE:
        P = calculate_priority_score_P(item)
        
        if P >= 10000:
            k_force.append((P, item))
        elif P > 0:
            candidates.append((P, item))

    # 排序强制清单 (确保高饥渴度的优先)
    k_force.sort(key=lambda x: x[0], reverse=True)
    
    # 计算剩余名额
    k_remaining = max(0, K_TARGET - len(k_force))
    
    # 排序候选清单 (P-Score 排序)
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    # 选出优先级填补模块
    k_priority = [item for p, item in candidates[:k_remaining]]
    
    final_list = [item for p, item in k_force] + k_priority
    
    # --- 打印输出 (保持简洁，不打印原始数据) ---
    print("-" * 50)
    print(f"📅 运行日期: {TODAY} | 目标: {K_TARGET} | 强制锁定: {len(k_force)}")
    print("-" * 50)
    
    for i, item in enumerate(final_list, 1):
        P_score = calculate_priority_score_P(item)
        R_val = calculate_review_factor_R(item)
        A_val = calculate_application_factor_A(item)
        
        print(f"[{i}] {item['key_module']} (ID: {item['id']})")
        print(f"    - P: {P_score} | R(逾期): {R_val} | A(饥渴): {A_val} 天 | CI: {item['CI']}")
    print("-" * 50)
    
    # 示范：更新第一个被选中的模块状态
    if final_list:
        print("\n--- 示范：更新第一个模块状态 (成功应用) ---")
        first_item = final_list[0]
        # 假设用户成功应用了这个模块
        update_module_state(first_item, is_applied_correctly=True) 

    return final_list

if __name__ == "__main__":
    # 确保数据库已初始化
    # 如果第一次运行，请先运行 database_manager.py 来导入初始数据
    
    generate_must_use_list()