# add_card_handler.py
import json
import sqlite3
import platform
from datetime import date, timedelta
from database_manager import DB_NAME, connect_db

CARDS_JSON_FILE = '../mod1_cards.json'
TODAY = date.today()  # 使用当前日期

def format_date_for_card(date_obj):
    """
    格式化日期为 M/D/YYYY 格式（去掉前导零）
    兼容 Windows 和 Unix 系统
    """
    if platform.system() == 'Windows':
        # Windows 使用 # 去掉前导零
        return date_obj.strftime('%#m/%#d/%Y')
    else:
        # Linux/Mac 使用 -
        return date_obj.strftime('%-m/%-d/%Y')

def add_new_card(card_data):
    """
    添加新卡片到数据库和JSON文件
    
    参数:
        card_data (dict): 卡片数据，必须包含以下字段:
            - cardId: 卡片ID
            - title: 卡片标题
            - Original: 原始内容
            - Tone: 语气
            - Explain: 解释
            - Usage: 用法
            - Extended: 扩展内容
            - Mysentence: 我的句子
            - Corrected: 修正
            - ExplainCorrected: 修正解释
            - Fluency: 流畅度
            - Createdtime: 创建时间
    
    返回:
        bool: 是否成功添加
    """
    try:
        # 1. 验证必填字段
        required_fields = ['cardId', 'title']
        for field in required_fields:
            if field not in card_data or not card_data[field]:
                print(f"❌ 错误: 缺少必填字段 '{field}'")
                return False
        
        card_id = card_data['cardId']
        
        # 2. 检查卡片ID是否已存在
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT card_id FROM cards WHERE card_id = ?', (card_id,))
        if cursor.fetchone():
            print(f"❌ 错误: 卡片 ID '{card_id}' 已存在")
            conn.close()
            return False
        
        # 3. 设置默认值
        card_defaults = {
            'Original': '',
            'Tone': 'informal',
            'Explain': '',
            'Usage': '',
            'Extended': '',
            'Mysentence': '',
            'Corrected': '',
            'ExplainCorrected': '',
            'Fluency': '1',
            'Createdtime': format_date_for_card(TODAY)  # 使用兼容的格式化函数
        }
        
        # 合并默认值和用户提供的数据
        complete_card_data = {**card_defaults, **card_data}
        
        # 4. 插入数据库
        # 设置初始 SRS 状态
        ci = 5
        lrd = TODAY - timedelta(days=5)
        lad = TODAY - timedelta(days=1)
        is_core = 0
        
        cursor.execute('''
            INSERT INTO cards (card_id, module_id, key_title, ci, lrd, lad, is_core)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            card_id,
            'mod1',  # 固定为 mod1
            complete_card_data['title'],
            ci,
            lrd.isoformat(),
            lad.isoformat(),
            is_core
        ))
        conn.commit()
        conn.close()
        print(f"✅ 卡片 '{card_id}' 已添加到数据库")
        
        # 5. 更新 JSON 文件
        try:
            with open(CARDS_JSON_FILE, 'r', encoding='utf-8') as f:
                cards_list = json.load(f)
        except FileNotFoundError:
            print(f"⚠️  警告: 找不到 {CARDS_JSON_FILE}，将创建新文件")
            cards_list = []
        
        # 添加新卡片到列表
        cards_list.append(complete_card_data)
        
        # 写回 JSON 文件
        with open(CARDS_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(cards_list, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 卡片 '{card_id}' 已添加到 {CARDS_JSON_FILE}")
        print(f"🎉 新卡片添加成功！总计 {len(cards_list)} 张卡片")
        
        return True
        
    except Exception as e:
        print(f"❌ 添加卡片时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def delete_card(card_id):
    """
    从数据库和JSON文件中删除卡片
    
    参数:
        card_id (str): 要删除的卡片ID
    
    返回:
        bool: 是否成功删除
    """
    try:
        # 1. 从数据库删除
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cards WHERE card_id = ?', (card_id,))
        
        if cursor.rowcount == 0:
            print(f"❌ 错误: 卡片 ID '{card_id}' 不存在")
            conn.close()
            return False
        
        conn.commit()
        conn.close()
        print(f"✅ 卡片 '{card_id}' 已从数据库删除")
        
        # 2. 从 JSON 文件删除
        with open(CARDS_JSON_FILE, 'r', encoding='utf-8') as f:
            cards_list = json.load(f)
        
        # 过滤掉要删除的卡片
        updated_cards_list = [card for card in cards_list if card['cardId'] != card_id]
        
        if len(updated_cards_list) == len(cards_list):
            print(f"⚠️  警告: JSON 文件中未找到卡片 '{card_id}'")
        
        # 写回 JSON 文件
        with open(CARDS_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(updated_cards_list, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 卡片 '{card_id}' 已从 {CARDS_JSON_FILE} 删除")
        print(f"🎉 卡片删除成功！剩余 {len(updated_cards_list)} 张卡片")
        
        return True
        
    except Exception as e:
        print(f"❌ 删除卡片时出错: {e}")
        return False


def update_card(card_id, updated_data):
    """
    更新现有卡片的数据（仅更新JSON文件中的学习内容，不更新SRS状态）
    
    参数:
        card_id (str): 要更新的卡片ID
        updated_data (dict): 要更新的字段和值
    
    返回:
        bool: 是否成功更新
    """
    try:
        # 1. 更新数据库中的标题（如果有）
        if 'title' in updated_data:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute('UPDATE cards SET key_title = ? WHERE card_id = ?', 
                         (updated_data['title'], card_id))
            
            if cursor.rowcount == 0:
                print(f"❌ 错误: 卡片 ID '{card_id}' 不存在")
                conn.close()
                return False
            
            conn.commit()
            conn.close()
            print(f"✅ 数据库中卡片 '{card_id}' 的标题已更新")
        
        # 2. 更新 JSON 文件
        with open(CARDS_JSON_FILE, 'r', encoding='utf-8') as f:
            cards_list = json.load(f)
        
        # 查找并更新卡片
        card_found = False
        for card in cards_list:
            if card['cardId'] == card_id:
                card.update(updated_data)
                card_found = True
                break
        
        if not card_found:
            print(f"❌ 错误: JSON 文件中未找到卡片 '{card_id}'")
            return False
        
        # 写回 JSON 文件
        with open(CARDS_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(cards_list, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 卡片 '{card_id}' 已在 {CARDS_JSON_FILE} 中更新")
        print(f"🎉 卡片更新成功！")
        
        return True
        
    except Exception as e:
        print(f"❌ 更新卡片时出错: {e}")
        return False


def run_manual_test():
    """手动测试函数 - 仅在直接运行此文件时执行"""
    # 示例 1: 添加新卡片
    new_card = {
        'cardId': 'mod1_card_14',
        'title': 'Test Card Title',
        'Original': 'This is a test card',
        'Tone': 'formal',
        'Explain': 'This is just for testing',
        'Mysentence': 'This is my example sentence'
    }
    
    print("=== 测试添加新卡片 ===")
    add_new_card(new_card)
    
    # 示例 2: 更新卡片
    print("\n=== 测试更新卡片 ===")
    update_card('mod1_card_14', {
        'title': 'Updated Test Card Title',
        'Explain': 'This explanation has been updated'
    })
    
    # 示例 3: 删除卡片
    print("\n=== 测试删除卡片 ===")
    delete_card('mod1_card_14')


if __name__ == '__main__':
    run_manual_test()