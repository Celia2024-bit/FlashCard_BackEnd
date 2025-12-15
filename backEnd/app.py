import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import time

# ==========================================================
# 🚨 关键配置区域 (已使用您提供的正确配置) 🚨
# ==========================================================

# 1. 您的 Supabase 项目 URL
SUPABASE_URL = "https://aefuqtzueqwjfhebfhrg.supabase.co" 

# 2. 您的 Supabase Anon Public Key (现已修正)
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFlZnVxdHp1ZXF3amZoZWJmaHJnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU3MjkxODEsImV4cCI6MjA4MTMwNTE4MX0.ydj2OKZX9ciJXXaStoXDqWXzG_xxyy7w-EXn2IooAfA" 

# --- 内部配置 ---
MODULE_TO_TABLE = {
    'mod1': 'mod1_cards', # Supabase 表名
    'mod2': 'mod2_cards', # Supabase 表名
}

# --- Flask 应用初始化 ---
app = Flask(__name__)
CORS(app) 

# --- 请求头：包含 Supabase 认证信息 ---
HEADERS = {
    'Content-Type': 'application/json',
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    # 🚨 关键修正：添加此行以强制 Supabase 返回插入的数据 🚨
    'Prefer': 'return=representation' 
}
# --- 辅助函数：封装 Supabase 请求 ---

def supabase_fetch(method, module_id, params=None, json_data=None):
    """
    封装对 Supabase PostgREST API 的 HTTP 请求
    """
    table_name = MODULE_TO_TABLE.get(module_id)
    if not table_name:
        raise ValueError(f"未知模块: {module_id}")
        
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    
    response = requests.request(
        method=method,
        url=url,
        headers=HEADERS,
        params=params, 
        json=json_data  
    )

    if not response.ok:
        error_msg = response.text or response.reason
        # 抛出 Supabase API 错误
        raise Exception(f"Supabase API Error {response.status_code}: {error_msg}")
        
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return []

def transform_from_supabase(records):
    """
    将 Supabase 返回的记录转换为前端所需的卡片格式
    """
    cards = []
    for record in records:
        if isinstance(record, dict) and 'cardid' in record and 'data' in record:
            # 合并 cardid 和 data 字段内容，确保 cardid 存在
            cards.append({**record['data'], 'cardid': record['cardid']})
    return cards

# --- 辅助函数：处理初始数据导入 ---
def initialize_data(module_id):
    # 1. 检查 Supabase 表中是否有数据
    try:
        table_name = MODULE_TO_TABLE[module_id]
        
        # 🚨 修正检查逻辑：只尝试获取一条记录 🚨
        check_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table_name}",
            headers=HEADERS,
            params={'select': 'cardid', 'limit': 1} # 只获取 'cardid' 字段的一条记录
        )
        check_response.raise_for_status()
        
        # 检查返回的 JSON 列表是否为空
        if len(check_response.json()) > 0:
            return # 表格已有数据，跳过导入
            
    except Exception as e:
        print(f"❌ 初始数据检查失败（{module_id}）: {e}")
        return

    # 2. 如果表为空，则从本地 JSON 文件加载数据
    try:
        filename = f'{module_id}_cards.json'
        with open(filename, 'r', encoding='utf-8') as f:
            initial_data = json.load(f)
        
        data_to_insert = []
        for card in initial_data:
            # 准备插入 Supabase 的格式：将整个卡片对象放到 data 字段，cardid 单独提取
            data_to_insert.append({
                'cardid': card.get('cardid'),
                'data': card
            })
            
        if data_to_insert:
            # 3. 批量插入到 Supabase (使用 on_conflict 避免初始数据重复插入失败)
            # 注意：Supabase API 的批量 POST 行为可能需要额外处理，这里使用最简模型
            requests.post(
                f"{SUPABASE_URL}/rest/v1/{table_name}",
                headers=HEADERS,
                json=data_to_insert,
                params={'on_conflict': 'cardid'} 
            ).raise_for_status()
            
            print(f"📥 成功将 {module_id} 的 {len(initial_data)} 条初始数据导入 Supabase")
        
    except FileNotFoundError:
        print(f"⚠️ 警告: 找不到初始数据文件 {filename}，跳过导入。")
    except Exception as e:
        print(f"❌ 初始数据导入失败（{module_id}）: {e}")


# --- 应用程序上下文中的初始化检查 ---
# 首次收到请求时触发连接和数据检查
@app.before_request
def check_initial_data():
    if not hasattr(app, 'initial_data_checked'):
        print("--- 尝试连接 Supabase 并检查初始数据 ---")
        # 如果这里失败，前端的 API 调用也会失败，并返回 500
        initialize_data('mod1')
        initialize_data('mod2')
        app.initial_data_checked = True 


# ==========================================================
# API 路由定义 (RESTful 风格)
# ==========================================================

# 1. GET: 获取所有卡片 (对应 loadCardsData)
@app.route('/api/<module_id>/cards', methods=['GET'])
def get_all_cards(module_id):
    """GET /api/mod1/cards"""
    try:
        # 获取所有 cardid 和 data 字段
        supabase_records = supabase_fetch('GET', module_id, params={'select': 'cardid,data'})
        cards = transform_from_supabase(supabase_records)
        
        return jsonify(cards), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 2. POST: 添加新卡片 (对应 addCard)
@app.route('/api/<module_id>/cards', methods=['POST'])
def add_card(module_id):
    """POST /api/mod1/cards"""
    try:
        new_card_data = request.json
        # 1. 确保使用小写 'cardid'
        card_id = new_card_data.get('cardid') 
        
        if not card_id:
            import time
            card_id = f"{module_id}_card_{int(time.time())}"
            new_card_data['cardid'] = card_id

        data_to_insert = {
            'cardid': card_id,
            'data': new_card_data
        }

        # 2. 插入数据 (Supabase 默认返回插入的记录)
        result = supabase_fetch('POST', module_id, json_data=data_to_insert)
        
        # 🚨 安全检查：确保 Supabase 返回了记录 🚨
        if not result or len(result) == 0:
            # RLS 阻止了 INSERT 或阻止了返回数据
            raise Exception("Supabase 插入卡片失败。请检查 RLS 策略或数据库唯一约束。")
        
        # 3. 转换并返回新卡片 (注意使用小写 'cardid' 的转换)
        new_card = {**result[0]['data'], 'cardid': result[0]['cardid']} 
        
        return jsonify({"success": True, "card": new_card}), 201

    except Exception as e:
        # 这个错误将会是您在第二个弹窗中看到的错误
        return jsonify({"success": False, "error": str(e)}), 500

# 3. PUT: 更新卡片 (对应 updateCard)
@app.route('/api/<module_id>/cards/<card_id>', methods=['PUT'])
def update_card(module_id, card_id):
    """PUT /api/mod1/cards/mod1_card_1"""
    try:
        updates = request.json
        updates.pop('cardid', None)
        
        # 构建更新内容：只更新 Supabase 表中的 data 字段
        # 注意：这里需要确保 Supabase 的 RLS (行级安全) 策略允许更新。
        data_to_update = {'data': updates}

        # PATCH 到 Supabase，使用 params 进行过滤 (WHERE cardid = 'eq.card_id')
        result = supabase_fetch(
            'PATCH', 
            module_id, 
            params={'cardid': f'eq.{card_id}'}, 
            json_data=data_to_update
        )

        if not result:
            return jsonify({'error': f'未找到卡片: {card_id} 或更新失败 (可能是 RLS 策略阻止)'}), 404
        
        # 重新获取更新后的卡片信息
        updated_card = transform_from_supabase(result)[0]
        return jsonify({"success": True, "card": updated_card}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 4. DELETE: 删除卡片 (对应 deleteCard)
@app.route('/api/<module_id>/cards/<card_id>', methods=['DELETE'])
def delete_card(module_id, card_id):
    """DELETE /api/mod1/cards/mod1_card_1"""
    try:
        # DELETE 请求，使用 params 进行过滤 (WHERE cardid = 'eq.card_id')
        supabase_fetch(
            'DELETE', 
            module_id, 
            params={'cardid': f'eq.{card_id}'}
        )
            
        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 5. POST: 重置为原始 JSON 数据 (对应 resetToOriginal)
@app.route('/api/<module_id>/reset', methods=['POST'])
def reset_cards(module_id):
    """POST /api/mod1/reset"""
    try:
        # 1. 清空 Supabase 表中的所有数据
        supabase_fetch('DELETE', module_id, params={'cardid': 'not.is.null'}) 
        
        # 2. 从本地 JSON 文件重新导入数据
        filename = f'{module_id}_cards.json'
        with open(filename, 'r', encoding='utf-8') as f:
            initial_data = json.load(f)
            
        data_to_insert = [
            {'cardid': card.get('cardid'), 'data': card}
            for card in initial_data
        ]
        
        if data_to_insert:
            # 3. 批量插入
            requests.post(
                f"{SUPABASE_URL}/rest/v1/{MODULE_TO_TABLE[module_id]}",
                headers=HEADERS,
                json=data_to_insert,
                params={'on_conflict': 'cardid'}
            ).raise_for_status()

        count = len(initial_data)
        return jsonify({"success": True, "message": f"模块 {module_id} 已重置", "count": count})
    except Exception as e:
        return jsonify({"success": False, "error": f"重置失败: {e}"}), 500

# 6. POST: 导入卡片数据 (对应 importCardsFromFile)
@app.route('/api/<module_id>/import', methods=['POST'])
def import_cards(module_id):
    """POST /api/mod1/import"""
    try:
        data = request.json
        cards_to_import = data.get('cards')
        
        if not isinstance(cards_to_import, list):
            return jsonify({'error': '导入数据必须是 JSON 数组'}), 400

        # 1. 清空当前 Supabase 表
        supabase_fetch('DELETE', module_id, params={'cardid': 'not.is.null'})

        # 2. 批量插入新数据
        data_to_insert = [
            {'cardid': card.get('cardid'), 'data': card}
            for card in cards_to_import
        ]

        if data_to_insert:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/{MODULE_TO_TABLE[module_id]}",
                headers=HEADERS,
                json=data_to_insert,
                params={'on_conflict': 'cardid'}
            ).raise_for_status()


        count = len(cards_to_import)
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"success": False, "error": f"导入失败: {e}"}), 500


# ==========================================================
# 启动 Flask 服务器
# ==========================================================
if __name__ == '__main__':
    # 强制不使用 debug 模式，避免某些环境下的重复启动问题
    app.run(debug=False, port=5000)