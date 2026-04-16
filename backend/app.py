import pyodbc
import re,uuid,time,hashlib
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- 1. 初始化Flask应用 ---
app = Flask(__name__)
# ---配置一个更强大、更明确的CORS策略 ---
# 这将解决所有的预检请求(preflight)问题
CORS(
    app, 
    # 明确允许你的两个前端来源
    origins=["http://127.0.0.1:8000", "http://localhost:8000"], 
    # 允许携带Cookie或Authorization头
    supports_credentials=True,
    # 明确允许前端可以发送的请求头
    allow_headers=["Content-Type", "Authorization"] 
)

# --- 2. 数据库连接配置 ---
DB_CONFIG = {
    'driver': '{SQL Server}',
    'server': 'LAPTOP-9APGKT71',      # <-- 正确的SQL Server实例名称
    'database': 'Poe2_MarketDB',    # <-- 最终数据库名
    'trusted_connection': 'yes'
}

# --- 3. 【核心】用一个简单的字典来模拟Token存储 ---
# 在真实应用中，这应该使用Redis或数据库来持久化存储
# 格式: { '一个随机的token字符串': {'user_id': 1, 'username': 'testuser', 'timestamp': ...} }
ACTIVE_TOKENS = {}

def get_db_connection():
    try:
        return pyodbc.connect(';'.join(f'{k}={v}' for k, v in DB_CONFIG.items()))
    except Exception as e:
        print(f"数据库连接失败! 错误: {e}")
        return None

# --- 3. 词缀模板字典与辅助函数 ---

AFFIX_TEMPLATE_MAP = {
    # 基础属性
    'flat_life': {'pattern': '%to maximum Life%', 'values': 1},
    'flat_mana': {'pattern': '%to maximum Mana%', 'values': 1},
    'flat_es': {'pattern': '%to maximum Energy Shield%', 'values': 1},
    'life_regen': {'pattern': '%Life Regeneration per second%', 'values': 1},
    'mana_regen_rate': {'pattern': '%increased Mana Regeneration Rate%', 'values': 1},
    'flat_strength': {'pattern': '%to Strength%', 'values': 1},
    'flat_dexterity': {'pattern': '%to Dexterity%', 'values': 1},
    'flat_intelligence': {'pattern': '%to Intelligence%', 'values': 1},
    'flat_all_attributes': {'pattern': '%to all Attributes%', 'values': 1},
    'percent_strength': {'pattern': '%increased Strength%', 'values': 1},
    'percent_dexterity': {'pattern': '%increased Dexterity%', 'values': 1},
    'percent_intelligence': {'pattern': '%increased Intelligence%', 'values': 1},
    'flat_accuracy': {'pattern': '%to Accuracy Rating%', 'values': 1},
    'percent_accuracy': {'pattern': '%increased Accuracy Rating%', 'values': 1},

    # 抗性
    'fire_res': {'pattern': '%to Fire Resistance%', 'values': 1},
    'cold_res': {'pattern': '%to Cold Resistance%', 'values': 1},
    'lightning_res': {'pattern': '%to Lightning Resistance%', 'values': 1},
    'chaos_res': {'pattern': '%to Chaos Resistance%', 'values': 1},
    'all_ele_res': {'pattern': '%to all Elemental Resistances%', 'values': 1},
    'max_fire_res': {'pattern': '%to Maximum Fire Resistance%', 'values': 1},
    'max_cold_res': {'pattern': '%to Maximum Cold Resistance%', 'values': 1},
    'max_lightning_res': {'pattern': '%to Maximum Lightning Resistance%', 'values': 1},
    
    # 伤害 - 增加百分比
    'inc_phys_damage': {'pattern': '%increased Physical Damage%', 'values': 1},
    'inc_fire_damage': {'pattern': '%increased Fire Damage%', 'values': 1},
    'inc_cold_damage': {'pattern': '%increased Cold Damage%', 'values': 1},
    'inc_lightning_damage': {'pattern': '%increased Lightning Damage%', 'values': 1},
    'inc_chaos_damage': {'pattern': '%increased Chaos Damage%', 'values': 1},
    'inc_ele_damage': {'pattern': '%increased Elemental Damage%', 'values': 1},
    'inc_ele_damage_with_attacks': {'pattern': '%increased Elemental Damage with Attacks%', 'values': 1},
    'inc_spell_damage': {'pattern': '%increased Spell Damage%', 'values': 1},
    'inc_projectile_damage': {'pattern': '%increased Projectile Damage%', 'values': 1},
    'inc_area_damage': {'pattern': '%increased Area of Effect%', 'values': 1}, # Note: Often referred to as Area Damage

       # 伤害 - 附加点伤,字符串匹配问题未解决(也可改数据库结构解决)
   # 'adds_phys_damage': {'pattern': '%Adds # to # Physical Damage%', 'values': 2},
   # 'adds_phys_damage_attacks': {'pattern': '%Adds # to # Physical Damage to Attacks%', 'values': 2},
   # 'adds_fire_damage': {'pattern': '%Adds # to # Fire Damage%', 'values': 2},
   # 'adds_fire_damage_attacks': {'pattern': '%Adds # to # Fire damage to Attacks%', 'values': 2},
   # 'adds_cold_damage': {'pattern': '%Adds # to # Cold Damage%', 'values': 2},
   # 'adds_cold_damage_attacks': {'pattern': '%Adds # to # Cold Damage to Attacks%', 'values': 2},
   # 'adds_lightning_damage': {'pattern': '%Adds # to # Lightning Damage%', 'values': 2},
   # 'adds_lightning_damage_attacks': {'pattern': '%Adds # to # Lightning Damage to Attacks%', 'values': 2},
    
    # 暴击
    'inc_crit_chance': {'pattern': '%increased Critical Hit Chance%', 'values': 1},
    'percent_crit_chance': {'pattern': '%to Critical Hit Chance%', 'values': 1},
    'inc_crit_chance_spells': {'pattern': '%increased Critical Hit Chance for Spells%', 'values': 1},
    'inc_crit_chance_attacks': {'pattern': '%increased Critical Hit Chance for Attacks%', 'values': 1},
    'crit_damage_bonus': {'pattern': '%to Critical Damage Bonus%', 'values': 1},
    'inc_crit_damage_bonus': {'pattern': '%increased Critical Damage Bonus%', 'values': 1},
    
    # 速度
    'inc_attack_speed': {'pattern': '%increased Attack Speed%', 'values': 1},
    'inc_cast_speed': {'pattern': '%increased Cast Speed%', 'values': 1},
    'inc_move_speed': {'pattern': '%increased Movement Speed%', 'values': 1},
    'inc_projectile_speed': {'pattern': '%increased Projectile Speed%', 'values': 1},
    
    # 防御
    'inc_armour': {'pattern': '%increased Armour%', 'values': 1},
    'inc_evasion': {'pattern': '%increased Evasion Rating%', 'values': 1},
    'inc_es': {'pattern': '%increased Energy Shield%', 'values': 1},
    'inc_armour_evasion': {'pattern': '%increased Armour and Evasion%', 'values': 1},
    'inc_armour_es': {'pattern': '%increased Armour and Energy Shield%', 'values': 1},
    'inc_evasion_es': {'pattern': '%increased Evasion and Energy Shield%', 'values': 1},
    'flat_armour': {'pattern': '%to Armour%', 'values': 1},
    'flat_evasion': {'pattern': '%to Evasion Rating%', 'values': 1},
    'inc_block_chance': {'pattern': '%increased Block Chance%', 'values': 1},
    'stun_threshold': {'pattern': '%to Stun Threshold%', 'values': 1},
    'inc_stun_buildup': {'pattern': '%increased Stun Buildup%', 'values': 1},

    # 击中/击杀效果
    'life_on_hit': {'pattern': '%Life per Enemy Hit%', 'values': 1},
    'mana_on_hit': {'pattern': '%Mana per Enemy Hit%', 'values': 1},
    'life_on_kill': {'pattern': '%Life per Enemy Killed%', 'values': 1},
    'mana_on_kill': {'pattern': '%Mana per Enemy Killed%', 'values': 1},
    'life_leech': {'pattern': '%of Physical Attack Damage as Life%', 'values': 1},
    'mana_leech': {'pattern': '%of Physical Attack Damage as Mana%', 'values': 1},

    # 技能等级
    'level_of_all_skills': {'pattern': '%to Level of all # Skills%', 'values': 1},
    'level_of_melee_skills': {'pattern': '%to Level of all Melee Skills%', 'values': 1},
    'level_of_projectile_skills': {'pattern': '%to Level of all Projectile Skills%', 'values': 1},

    # 杂项
    'inc_rarity_items': {'pattern': '%increased Rarity of Items found%', 'values': 1},
    'reduced_attr_req': {'pattern': '%reduced Attribute Requirements%', 'values': 1},
    'inc_spirit': {'pattern': '%increased Spirit%', 'values': 1},
}
def get_sql_like_pattern_and_values(stat_id):
    return AFFIX_TEMPLATE_MAP.get(stat_id)

# --- 4. 辅助API接口 ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # 【安全简化】在真实应用中，这里需要验证哈希后的密码
    # cursor.execute("SELECT PasswordHash FROM Accounts WHERE Username = ?", username)
    # ... 验证逻辑 ...
    
    # 课设简化版：直接验证
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT AccountID FROM Accounts WHERE Username = ?", username)
    user_account = cursor.fetchone()
    conn.close()

    # 假设验证通过，得到了 user_account 对象
    
    if user_account:
        # 登录成功，生成一个独一无二的Token
        token = str(uuid.uuid4())
        # 在服务器内存中存储这个Token和用户信息
        ACTIVE_TOKENS[token] = {
            'user_id': user_account.AccountID,
            'username': username,
            'login_time': time.time()
        }
        print(f"用户 '{username}' 登录成功，生成的Token是: {token}")
        # 把Token和用户信息一起返回给前端
        return jsonify({
            "success": True, 
            "message": "Login successful", 
            "token": token,
            "username": username
        })
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

# 【新增】一个装饰器，用于保护需要登录才能访问的接口
from functools import wraps

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # 从请求头里获取 'Authorization'
        if 'Authorization' in request.headers:
            # 格式通常是 'Bearer a-long-token-string'
            token = request.headers['Authorization'].split(" ")[1]

        if not token or token not in ACTIVE_TOKENS:
            return jsonify({'message': 'Token is missing or invalid!'}), 401
        
        # 把用户信息注入到请求中，方便后续使用 (可选)
        current_user = ACTIVE_TOKENS[token]
        
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/api/logout', methods=['POST'])
@token_required # 我们可以保护这个接口，确保只有登录用户才能登出
def logout(current_user):
    # 从我们的ACTIVE_TOKENS字典中移除这个token
    token = request.headers['Authorization'].split(" ")[1]
    if token in ACTIVE_TOKENS:
        del ACTIVE_TOKENS[token]
        print(f"用户 '{current_user['username']}' 的Token已清除，成功登出。")
    
    return jsonify({"success": True, "message": "Logout successful"})

# app.py -> add_item (最终的、极简化、直接INSERT版)


@app.route('/api/item', methods=['POST'])
@token_required
def add_item(current_user):
    # 1. 获取前端发送的、结构化的newItem对象
    item_data = request.get_json()
    if not item_data or not item_data.get('ItemName'):
        return jsonify({"success": False, "message": "Item Name is required."}), 400

    print(f"收到来自用户'{current_user['username']}'的新物品请求:", item_data)
    
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Database connection failed."}), 500
    cursor = conn.cursor()

    try:
        # --- 核心：直接、简单地插入数据 ---
        
        # 2. 生成唯一的ItemID
        item_id_source = f"{current_user['username']}{time.time()}{item_data.get('ItemName')}"
        item_id = hashlib.sha256(item_id_source.encode('utf-8')).hexdigest()
        
        # 3. 处理外键依赖 (这部分依然是必要的，以获取ID)
        user_id = current_user['user_id']

        #    同时，我们获取前端传来的UserName，用于在Users表里创建或确认记录
        seller_name_from_form = item_data.get('UserName')
        
        cursor.execute("SELECT UserID FROM Users WHERE UserName = ?", seller_name_from_form)
        user_row = cursor.fetchone()
        
        if user_row:
            # 如果卖家已存在，直接获取他的UserID
            seller_user_id = user_row[0]
            print(f"复用已存在的卖家 '{seller_name_from_form}', UserID: {seller_user_id}")
        else:
            # 如果卖家不存在，向Users表插入一个新记录，并获取新生成的UserID
            print(f"新卖家 '{seller_name_from_form}'，正在创建记录...")
            cursor.execute("INSERT INTO Users (UserName) OUTPUT INSERTED.UserID VALUES (?)", seller_name_from_form)
            seller_user_id = cursor.fetchone()[0]
            print(f"新卖家创建成功, UserID: {seller_user_id}")

        #CurrencyID
        currency_name = item_data.get('CurrencyName', 'N/A')
        cursor.execute("SELECT CurrencyID FROM Currencies WHERE CurrencyName = ?", currency_name)
        currency_row = cursor.fetchone()
        currency_id = currency_row[0] if currency_row else cursor.execute("INSERT INTO Currencies (CurrencyName) OUTPUT INSERTED.CurrencyID VALUES (?)", currency_name).fetchone()[0]

        #CategoryID 
        category_name = item_data.get('ItemCategory', 'Unknown')
        cursor.execute("SELECT CategoryID FROM ItemCategories WHERE CategoryName = ?", category_name)
        category_row = cursor.fetchone()
        category_id = category_row[0] if category_row else cursor.execute("INSERT INTO ItemCategories (CategoryName) OUTPUT INSERTED.CategoryID VALUES (?)", category_name).fetchone()[0]
        
        #SkillID 
        skill_name = item_data.get('SkillName')
        skill_id = None # 默认为NULL
        if skill_name: # 只有在前端提供了技能名时才处理
            cursor.execute("SELECT SkillID FROM Skills WHERE SkillName = ?", skill_name)
            skill_row = cursor.fetchone()
            skill_id = skill_row[0] if skill_row else cursor.execute("INSERT INTO Skills (SkillName) OUTPUT INSERTED.SkillID VALUES (?)", skill_name).fetchone()[0]

        # 4. 【关键】构建一个直接的、简单的INSERT语句到Items表
        items_sql = """
            INSERT INTO Items 
            (ItemID, ItemName, BaseType,ItemImageURL, Quality, IsCorrupted, 
             ItemLevel, RequiredLevel, RequiredStr, RequiredDex, RequiredInt, 
             PriceAmount, ListedAtText, UserID, CurrencyID, CategoryID, SkillID)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            item_id,
            item_data.get('ItemName'), item_data.get('BaseType'), 
            item_data.get('ItemImageURL'), item_data.get('Quality', 0),
            bool(item_data.get('IsCorrupted', False)),
            item_data.get('ItemLevel'), item_data.get('RequiredLevel'), item_data.get('RequiredStr'),
            item_data.get('RequiredDex'), item_data.get('RequiredInt'),
            item_data.get('PriceAmount'), 'listed just now',
            seller_user_id, currency_id, category_id, skill_id
        )
        cursor.execute(items_sql, params)
        
        # 5. 【关键】直接、简单地插入到扩展表
        #    我们直接从item_data里获取值，如果不存在，.get()方法会返回None，数据库列需要允许NULL
        
        #插入User表
        user_sql ="""
            INSERT INTO Users 
            (UserID,UserName)
            VALUES (?, ?)
        """
        u_params = (
            user_id,
            item_data.get('UserName')
        )

        # 插入WeaponProperties
        weapon_sql = """
            INSERT INTO WeaponProperties 
            (ItemID, PhysicalDmgMin, PhysicalDmgMax, CritChance, AttacksPerSecond)
            VALUES (?, ?, ?, ?, ?)
        """
        w_params = (
            item_id,
            item_data.get('PhysicalDmgMin'), item_data.get('PhysicalDmgMax'),
            item_data.get('CritChance'), item_data.get('AttacksPerSecond')
        )
        # 只有在至少有一个武器属性存在时才执行插入
        if any(v is not None for v in w_params[1:]):
            cursor.execute(weapon_sql, w_params)

        # ... 为 ArmorProperties 和 ShieldProperties 添加完全类似的、简单的INSERT语句 ...

        # 6. 【关键】直接、简单地插入词缀
        affixes = item_data.get('AllAffixes', [])
        if affixes:
            for affix_text in affixes:
                cursor.execute("INSERT INTO Affixes (ItemID, AffixText, AffixType) VALUES (?, ?, ?)", 
                               item_id, affix_text, 'Explicit')

        # 7. 提交事务
        conn.commit()
        return jsonify({"success": True, "message": "Item added successfully!", "newItemID": item_id})

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": f"An error occurred: {e}"}), 500
    finally:
        if conn: conn.close()


@app.route('/api/item/<item_id>', methods=['DELETE'])
@token_required # <-- 同样保护这个接口
def buy_item(current_user, item_id):
    """
    处理购买（逻辑上是删除）物品的请求。
    :param current_user: 由 @token_required 装饰器注入的、包含用户信息（如username）的字典。
    :param item_id: 从URL路径中获取的、要删除的物品的唯一ID。
    """
    
    print(f"用户 '{current_user['username']}' 正在尝试购买物品ID: {item_id}")

    # 1. 参数验证
    if not item_id:
        return jsonify({"success": False, "message": "Item ID is required."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"success": False, "message": "Database connection error."}), 500

    cursor = conn.cursor()

    try:
        # 2. 检查物品是否存在，避免无效的删除操作
        cursor.execute("SELECT COUNT(1) FROM Items WHERE ItemID = ?", item_id)
        if cursor.fetchone()[0] == 0:
            print(f"购买失败：物品ID {item_id} 不存在。")
            return jsonify({"success": False, "message": "Item not found or already sold."}), 404

        # 3. 执行删除操作
        # 由于我们在数据库中设置了级联删除(ON DELETE CASCADE)，
        # 删除Items表中的记录会自动删除所有相关联的记录
        # (在WeaponProperties, ArmorProperties, Affixes等表中)。
        print(f"正在从数据库中删除物品ID: {item_id}")
        cursor.execute("DELETE FROM Items WHERE ItemID = ?", item_id)
        
        # 4. 提交数据库事务
        conn.commit()
        
        # cursor.rowcount会返回受影响的行数，如果大于0说明删除成功
        if cursor.rowcount > 0:
            print(f"物品ID {item_id} 已被成功购买和移除。")
            return jsonify({"success": True, "message": f"Item {item_id} has been purchased."})
        else:
            # 这是一个理论上的边界情况，以防万一
            print(f"购买失败：物品ID {item_id} 在删除时未找到。")
            return jsonify({"success": False, "message": "Item could not be removed."}), 404

    except Exception as e:
        # 如果在数据库操作中发生任何错误，回滚事务
        conn.rollback()
        print(f"购买物品ID {item_id} 时发生数据库错误: {e}")
        return jsonify({"success": False, "message": f"An internal error occurred: {e}"}), 500
    finally:
        # 确保数据库连接总是被关闭
        if conn:
            conn.close()

@app.route('/api/stats', methods=['GET'])
def get_available_stats():
    stats_data = [{"id": key, "label": value['pattern'].replace('%', '').replace('# to #', '#-#').replace('#', '#')} 
                  for key, value in AFFIX_TEMPLATE_MAP.items()]
    stats_data.sort(key=lambda x: x['label'])
    return jsonify(stats_data)

@app.route('/api/categories', methods=['GET'])
def get_available_categories():
    # ... (此接口逻辑不变) ...
    pass


# --- 5. 核心搜索接口 (最终的、融合了所有功能的版本) ---
@app.route('/api/search', methods=['POST'])
def search_items():
    filters = request.get_json() or {}
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        
        params = []

        # --- 步骤A: 构建词缀过滤的CTE (如果需要) ---
        stat_filter_cte = ""
        # 【关键】这里我们不再把词缀参数放到主params列表，而是为CTE单独创建一个

        if 'stat_filters' in filters and filters.get('stat_filters'):
            intersect_clauses = []
    
            for i, stat_filter in enumerate(filters['stat_filters']):

                if not stat_filter.get('active', False): # 如果没有active字段或其值为false，就跳过这个过滤器
                    continue

                stat_id, min_val, max_val = stat_filter.get('id'), stat_filter.get('min'), stat_filter.get('max')
                template_info = get_sql_like_pattern_and_values(stat_id)
                if not template_info: continue

                # --- 【核心】构建终极的、多情况的数值提取SQL ---
                # 我们用一个CASE WHEN语句来为不同类型的词缀选择不同的解析方法
                value_extraction_sql = f"""
                    CASE 
                        -- 情况1: 处理 "Adds # to # Damage" 类型的词缀
                        WHEN Affixes.AffixText LIKE '%Adds % to % Damage%' THEN
                            -- 计算平均值
                            (
                                -- 提取第一个数字
                                TRY_CAST(
                                    SUBSTRING(
                                        Affixes.AffixText, 
                                        PATINDEX('%]Adds %', Affixes.AffixText) + 6, -- 从 "Adds " 后面开始找
                                        CHARINDEX(' ', Affixes.AffixText, PATINDEX('%]Adds %', Affixes.AffixText) + 6) - (PATINDEX('%]Adds %', Affixes.AffixText) + 6)
                                    ) AS FLOAT
                                )
                                +
                                -- 提取第二个数字
                                TRY_CAST(
                                    SUBSTRING(
                                        Affixes.AffixText,
                                        CHARINDEX(' to ', Affixes.AffixText, PATINDEX('%]Adds %', Affixes.AffixText)) + 4,
                                        CHARINDEX(' ', Affixes.AffixText, CHARINDEX(' to ', Affixes.AffixText, PATINDEX('%]Adds %', Affixes.AffixText)) + 4) - (CHARINDEX(' to ', Affixes.AffixText, PATINDEX('%]Adds %', Affixes.AffixText)) + 4)
                                    ) AS FLOAT
                                )
                            ) / 2.0

                        -- 情况2: 处理其他只含单个核心数值的词缀
                        ELSE
                            -- 这个逻辑提取出方括号之外的第一个数字
                            TRY_CAST(
                                REPLACE( -- 去掉百分号
                                    SUBSTRING(
                                        SUBSTRING(Affixes.AffixText, ISNULL(CHARINDEX(']', Affixes.AffixText), 0) + 1, 8000), -- 从 ']' 后面开始截取
                                        PATINDEX('%[0-9.-]%', SUBSTRING(Affixes.AffixText, ISNULL(CHARINDEX(']', Affixes.AffixText), 0) + 1, 8000)), -- 找到新字符串里的第一个数字
                                        PATINDEX('%[^0-9.-]%', SUBSTRING(SUBSTRING(Affixes.AffixText, ISNULL(CHARINDEX(']', Affixes.AffixText), 0) + 1, 8000), PATINDEX('%[0-9.-]%', SUBSTRING(Affixes.AffixText, ISNULL(CHARINDEX(']', Affixes.AffixText), 0) + 1, 8000)), 8000) + ' ') - 1
                                    ),
                                '%', '')
                            AS FLOAT)
                    END
                """

                clause = f"(SELECT ItemID FROM Affixes WHERE AffixText LIKE ?"
                clause_params = [template_info['pattern']]
        
                # 将数值比较应用到这个复杂的表达式上
                if min_val is not None:
                    clause += f" AND ({value_extraction_sql}) >= ?"
                    clause_params.append(float(min_val))
                if max_val is not None:
                    clause += f" AND ({value_extraction_sql}) <= ?"
                    clause_params.append(float(max_val))
                clause += ")"
        
                intersect_clauses.append(clause)
                params.extend(clause_params)

            if intersect_clauses:
                stat_filter_cte = "WITH FilteredByStats AS (" + " INTERSECT ".join(intersect_clauses) + ")"

        # --- 步骤B: 构建包含所有数据和计算的主查询部分 ---
        main_data_query = f"""
            SELECT 
                    i.ItemID,
                    -- Items表的其他所有公共属性
                    i.ItemName, i.BaseType, i.ItemImageURL, i.Quality, i.IsCorrupted, 
                    i.ItemLevel, i.RequiredLevel, i.RequiredStr, i.RequiredDex, i.RequiredInt,
                    i.PriceAmount, i.ListedAtText,
                    -- 来自JOIN表的列
                    u.UserName, c.CurrencyName, cat.CategoryName, s.SkillName,
                    -- WeaponProperties表的列
                    wp.PhysicalDmgMin, wp.PhysicalDmgMax, wp.ColdDmgMin, wp.ColdDmgMax, 
                    wp.FireDmgMin, wp.FireDmgMax, wp.LightningDmgMin, wp.LightningDmgMax,
                    wp.ChaosDmgMin, wp.ChaosDmgMax,
                    wp.CritChance, wp.AttacksPerSecond, wp.ReloadTime, wp.Spirit,
                    -- ArmorProperties表的列
                    ap.Armour, ap.Evasion, ap.EnergyShield,
                    -- ShieldProperties表的列
                    sp.BlockChance,
                    -- 计算总DPS
                    (
                        (ISNULL(wp.PhysicalDmgMin, 0) + ISNULL(wp.PhysicalDmgMax, 0)) / 2.0 +
                        (ISNULL(wp.FireDmgMin, 0) + ISNULL(wp.FireDmgMax, 0)) / 2.0 +
                        (ISNULL(wp.ColdDmgMin, 0) + ISNULL(wp.ColdDmgMax, 0)) / 2.0 +
                        (ISNULL(wp.LightningDmgMin, 0) + ISNULL(wp.LightningDmgMax, 0)) / 2.0 +
                        (ISNULL(wp.ChaosDmgMin, 0) + ISNULL(wp.ChaosDmgMax, 0)) / 2.0
                    ) * ISNULL(wp.AttacksPerSecond, 0) AS dps,
                    -- 计算物理DPS
                    (
                        (ISNULL(wp.PhysicalDmgMin, 0) + ISNULL(wp.PhysicalDmgMax, 0)) / 2.0
                    ) * ISNULL(wp.AttacksPerSecond, 0) AS phys_dps,
                    -- 计算元素DPS
                    (
                        (ISNULL(wp.FireDmgMin, 0) + ISNULL(wp.FireDmgMax, 0)) / 2.0 +
                        (ISNULL(wp.ColdDmgMin, 0) + ISNULL(wp.ColdDmgMax, 0)) / 2.0 +
                        (ISNULL(wp.LightningDmgMin, 0) + ISNULL(wp.LightningDmgMax, 0)) / 2.0
                    ) * ISNULL(wp.AttacksPerSecond, 0) AS ele_dps
            FROM Items i
            LEFT JOIN Users u ON i.UserID = u.UserID
            LEFT JOIN Currencies c ON i.CurrencyID = c.CurrencyID
            LEFT JOIN ItemCategories cat ON i.CategoryID = cat.CategoryID
            LEFT JOIN Skills s ON i.SkillID = s.SkillID
            LEFT JOIN WeaponProperties wp ON i.ItemID = wp.ItemID
            LEFT JOIN ArmorProperties ap ON i.ItemID = ap.ItemID
            LEFT JOIN ShieldProperties sp ON i.ItemID = sp.ItemID
            {'JOIN FilteredByStats fbs ON i.ItemID = fbs.ItemID' if stat_filter_cte else ''}
        """

        # --- 步骤C: 将主查询包装成子查询，并应用所有静态过滤器 ---
        final_query = f"""
            {stat_filter_cte}
            SELECT *,
                   (SELECT STRING_AGG(aff.AffixText, '|') FROM Affixes aff WHERE aff.ItemID = ci.ItemID) AS AllAffixes
            FROM ({main_data_query}) AS ci
        """
        where_clauses = []
        
        # 静态过滤器映射表 (所有列都来自虚拟表ci)
        filter_map = {
            # TYPE FILTERS
            'item_category': ('ci.CategoryName', '='),
            'item_rarity': ('ci.Rarity', '='), # 假设Items表有Rarity列
            'item_level_min': ('ci.ItemLevel', '>='),
            'item_level_max': ('ci.ItemLevel', '<='),
            'quality_min': ('ci.Quality', '>='),
            'quality_max': ('ci.Quality', '<='),
            # EQUIPMENT FILTERS
            'damage_min': ('ci.PhysicalDmgMin', '>='), # 这是一个简化的总点伤，实际情况可能更复杂
            'damage_max': ('ci.PhysicalDmgMax', '<='),
            'aps_min': ('ci.AttacksPerSecond', '>='),
            'aps_max': ('ci.AttacksPerSecond', '<='),
            'crit_min': ('ci.CritChance', '>='),
            'crit_max': ('ci.CritChance', '<='),
            'dps_min': ('ci.dps', '>='), # 直接按计算出的别名过滤
            'dps_max': ('ci.dps', '<='),
            'phys_dps_min': ('ci.phys_dps', '>='),
            'phys_dps_max': ('ci.phys_dps', '<='),
            'ele_dps_min': ('ci.ele_dps', '>='),
            'ele_dps_max': ('ci.ele_dps', '<='),
            'reload_min': ('ci.ReloadTime', '>='),
            'reload_max': ('ci.ReloadTime', '<='),
            'armour_min': ('ci.Armour', '>='),
            'armour_max': ('ci.Armour', '<='),
            'evasion_min': ('ci.Evasion', '>='),
            'evasion_max': ('ci.Evasion', '<='),
            'es_min': ('ci.EnergyShield', '>='),
            'es_max': ('ci.EnergyShield', '<='),
            'block_min': ('ci.BlockChance', '>='),
            'block_max': ('ci.BlockChance', '<='),
            'spirit_min': ('ci.Spirit', '>='),
            'spirit_max': ('ci.Spirit', '<='),
            'sockets_min': ('ci.Sockets', '>='),# 假设Items表有Sockets列
            'sockets_max': ('ci.Sockets', '<='),
            # ... 添加所有其他min/max过滤器的映射 ...
            # REQUIREMENTS FILTERS
            'req_level_min': ('ci.RequiredLevel', '>='),
            'req_level_max': ('ci.RequiredLevel', '<='),
            'req_str_min': ('ci.RequiredStr', '>='),
            'req_str_max': ('ci.RequiredStr', '<='),
            'req_dex_min': ('ci.RequiredDex', '>='),
            'req_dex_max': ('ci.RequiredDex', '<='),
            'req_int_min': ('ci.RequiredInt', '>='),
            'req_int_max': ('ci.RequiredInt', '<='),
            # TRADE FILTERS
            'seller_account': ('ci.UserName', 'LIKE'),
            #'collapse_listings': ('ci.CollapseListings', '='),# 假设后续添加Users表有CollapseListings列
            'listed_time': ('ci.LinkedAtText', '<='),
            'sale_type': ('ci.SaleType', '='),# 假设Users表有SaleType列
            'buyout_currency': ('ci.CurrencyName', '='),
            'buyout_min': ('ci.PriceAmount', '>='),
            'buyout_max': ('ci.PriceAmount', '<='),
        }

        for key, value in filters.items():
            if key == 'stat_filters' or value in [None, '', 'any']: continue
            if key in filter_map:
                col, op = filter_map[key]
                if op == 'LIKE': where_clauses.append(f"{col} LIKE ?"); params.append(f"%{value}%")
                else: where_clauses.append(f"{col} {op} ?"); params.append(value)
        
        if where_clauses:
            final_query += " WHERE " + " AND ".join(where_clauses)
        
        # --- 步骤D: 排序 ---
        sort_by = filters.get('sort_by', 'PriceAmount')
        allowed_sort_columns = {'PriceAmount', 'CritChance', 'ItemName', 'dps_total'}
        if sort_by not in allowed_sort_columns: sort_by = 'PriceAmount'
        final_query += f" ORDER BY ci.{sort_by} ASC" # 默认升序

        # --- DEBUG输出 ---
        print("\n--- [DEBUG] Final SQL Query ---"); print(final_query)
        print("--- [DEBUG] Parameters ---"); print(params); print("-" * 30)
        
        # --- 执行查询并返回结果 ---
        cursor.execute(final_query, params)

        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))

            # 定义所有可能从数据库返回Decimal类型的字段列表
            decimal_fields = [
                'PriceAmount', 'CritChance', 'AttacksPerSecond', 
                'ReloadTime', 'BlockChance',
                'dps_total', 'dps_phys', 'dps_ele' # 别忘了我们计算出的DPS也是Decimal
            ]
            
            for field in decimal_fields:
                if row_dict.get(field) is not None:
                    try:
                        # 强制转换为浮点数
                        row_dict[field] = float(row_dict[field])
                    except (ValueError, TypeError):
                        # 如果转换失败（虽然不太可能），保持为None
                        row_dict[field] = None
    
            # 确保布尔值是真正的布尔值 (True/False)，而不是1/0
            if row_dict.get('IsCorrupted') is not None:
                row_dict['IsCorrupted'] = bool(row_dict['IsCorrupted'])

            if row_dict.get('AllAffixes'): row_dict['AllAffixes'] = row_dict['AllAffixes'].split('|')
            else: row_dict['AllAffixes'] = []
            results.append(row_dict)
        
        return jsonify(results)

    except Exception as e:
        print(f"查询时发生错误: {e}")
        return jsonify({"error": f"An error occurred: {e}"}), 500
    finally:
        if conn: conn.close()

# --- 6. 启动服务器 ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)