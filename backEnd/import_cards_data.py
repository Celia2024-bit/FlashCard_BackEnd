# import_cards_data.py (基于 mod1_cards.json 的修改版)
import sqlite3
import json
from datetime import date, timedelta
from database_manager import DB_NAME, connect_db 

# 核心修改点 1: 引用新的 JSON 文件名
CARDS_JSON_FILE = '../mod1_cards.json' 

# 假设的今天日期，用于设置初始状态
TODAY = date(2025, 12, 11) 

def create_cards_table():
    """创建新的卡片表"""
    conn = connect_db()
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

def import_all_cards_from_json():
    """读取 mod1_cards.json，注入初始 SRS 状态，并导入数据库"""
    create_cards_table()
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # 打开并加载 mod1_cards.json 文件
        with open(CARDS_JSON_FILE, 'r', encoding='utf-8') as f:
            # 核心修改点 2: mod1_cards.json 是一个卡片列表
            cards_list = json.load(f) 
    except FileNotFoundError:
        print(f"错误: 找不到 {CARDS_JSON_FILE} 文件，请确保文件存在。")
        conn.close()
        return

    cursor.execute('SELECT COUNT(*) FROM cards')
    if cursor.fetchone()[0] > 0:
        print("数据库中已有数据，跳过初始导入。")
        conn.close()
        return

    inserted_count = 0
    
    # 核心修改点 3: 直接遍历卡片列表
    for card_data in cards_list:
        card_id = card_data['cardId']
        # 核心修改点 4: 直接从卡片数据中获取 title
        key_title = card_data.get('title') or 'Untitled'
        
        # mod1_cards.json 中的数据都视为属于 'mod1'
        module_id = 'mod1' 

        # --- 注入初始 SRS 状态 (保持与原逻辑一致) ---
        ci = 5
        lrd = TODAY - timedelta(days=5) 
        lad = TODAY - timedelta(days=1)
        is_core = 0
        
        # 针对特定卡片的特殊状态（保持不变）
        if card_id == 'mod1_card_1': 
            ci = 100 
            lrd = TODAY - timedelta(days=105) 
            lad = TODAY - timedelta(days=31) 
            is_core = 0
        elif card_id == 'mod1_card_2': 
            ci = 1
            lrd = TODAY - timedelta(days=2) 
            lad = TODAY - timedelta(days=10)
            is_core = 1 
        
        cursor.execute('''
            INSERT INTO cards (card_id, module_id, key_title, ci, lrd, lad, is_core)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            card_id,
            module_id,
            key_title,
            ci,
            lrd.isoformat(),
            lad.isoformat(),
            is_core
        ))
        inserted_count += 1

    conn.commit()
    print(f"🎉 成功导入 {inserted_count} 条卡片到 {DB_NAME} 数据库中。")
    conn.close()

if __name__ == '__main__':
    # 运行此脚本以初始化数据库
    import_all_cards_from_json()