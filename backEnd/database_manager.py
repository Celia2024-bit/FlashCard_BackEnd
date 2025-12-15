import sqlite3
from datetime import date

DB_NAME = 'srs_data.db'

def connect_db():
    """连接数据库，并设置行工厂以支持通过字段名访问数据"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    return conn

# database_manager.py (替换 get_all_cards_srs_state 函数)

def get_all_cards_srs_state():
    """从数据库中读取所有 Module 1 卡片的 SRS 状态。"""
    conn = connect_db()
    cursor = conn.cursor()
    
    # *** 核心修改：WHERE module_id = 'mod1' ***
    cursor.execute("SELECT * FROM cards WHERE module_id = 'mod1'")
    rows = cursor.fetchall()
    conn.close()
    
    card_list = []
    
    for row in rows:
        card_dict = dict(row)
        
        # ... (数据类型转换保持不变) ...
        card_dict['LRD'] = date.fromisoformat(card_dict['lrd'])
        card_dict['LAD'] = date.fromisoformat(card_dict['lad'])
        card_dict['CI'] = card_dict['ci']
        card_dict['is_core'] = bool(card_dict['is_core']) 
        
        card_dict['id'] = card_dict['card_id'] # P-Score 算法依赖 'id' 字段
        
        card_list.append(card_dict)
        
    return card_list
    
def update_card_srs_state_in_db(card_state):
    """将更新后的卡片 SRS 状态写回数据库"""
    conn = connect_db()
    cursor = conn.cursor()

    # 将 date 对象转回字符串以便存入数据库
    lrd_str = card_state['LRD'].isoformat()
    lad_str = card_state['LAD'].isoformat()
    
    cursor.execute('''
        UPDATE cards SET ci=?, lrd=?, lad=?, is_core=? 
        WHERE card_id=?
    ''', (
        card_state['CI'],
        lrd_str,
        lad_str,
        1 if card_state['is_core'] else 0,
        card_state['card_id'] # 使用 card_id 作为更新依据
    ))
    
    conn.commit()
    conn.close()
    print(f"💾 卡片 {card_state['card_id']} 状态已更新并持久化。")

# 注意：我们不再需要 create_table 和 import_initial_data_from_json,
# 因为这些功能现在由 import_cards_data.py 处理。