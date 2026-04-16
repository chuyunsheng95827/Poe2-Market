import pyperclip
import time
import hashlib
import pyodbc
from bs4 import BeautifulSoup
import re

# --------------------------------------------------------------------------
# 1. 数据库连接配置 -> 连接到全新的 Poe2_MarketDB
# --------------------------------------------------------------------------
DB_CONFIG = {
    'driver': '{SQL Server}',
    'server': 'LAPTOP-9APGKT71',
    'database': 'Poe2_MarketDB', # <--- 已更新为你的最终数据库
    'trusted_connection': 'yes'
}

def get_db_connection():
    try:
        conn_str = ';'.join(f'{k}={v}' for k, v in DB_CONFIG.items())
        return pyodbc.connect(conn_str)
    except Exception as e:
        print(f"\n数据库连接失败! 错误: {e}")
        return None

# --------------------------------------------------------------------------
# 2. 核心函数 (最终架构适配版)
# --------------------------------------------------------------------------
def parse_and_save_data(html_content):
    if not html_content: return
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    results_container = soup.find('div', class_='results')
    if not results_container:
        print("警告：未能找到class为 'results' 的大容器！")
        conn.close()
        return

    item_elements = results_container.find_all('div', class_='row')
    print(f"\n检测到 {len(item_elements)} 个物品，开始处理...")
    
    for item in item_elements:
        item_id = None
        try:
            item_id = item.get('data-id')
            if not item_id: continue

            # --- 初始化所有数据容器 ---
            item_data = {'ItemID': item_id, 'IsCorrupted': 0, 'Quality': 0}
            weapon_props, armor_props, shield_props = {}, {}, {}
            affixes = []

            # --- 统一解析所有信息 ---
            
            # 解析右侧窗格：卖家和价格
            right_pane = item.find('div', class_='right')
            if right_pane:
                seller_info = right_pane.find('span', class_='profile-link'); item_data['SellerName'] = seller_info.find('a').text.strip() if seller_info else 'Unknown'
                listed_at_small = right_pane.find('small'); item_data['ListedAtText'] = listed_at_small.text.strip() if listed_at_small else 'Unknown'
                
                # 【最终修正】使用你之前成功的、更稳定的通货获取逻辑
                price_div = right_pane.find('div', class_='price')
                if price_div:
                    amount_span = price_div.find('span'); item_data['PriceAmount'] = float(re.sub(r'[^\d.]', '', amount_span.text.strip())) if amount_span else 0.0
                    currency_span_list = price_div.find_all('span')
                    if len(currency_span_list) > 1:
                        item_data['CurrencyName'] = currency_span_list[-1].text.strip()
                    else:
                        item_data['CurrencyName'] = 'N/A' # 如果找不到，给个默认值

            # 解析左侧窗格：图片
            left_pane = item.find('div', class_='left')
            if left_pane:
                icon_div = left_pane.find('div', class_='icon'); item_data['ItemImageURL'] = icon_div.find('img').get('src') if icon_div and icon_div.find('img') else None

            # 解析中间窗格：名称、基底、属性、词缀
            middle_pane = item.find('div', class_='middle')
            if middle_pane:
                # 名称和基底
                header_div = middle_pane.find('div', class_='itemHeader')
                if header_div:
                    item_name_exclusive, base_type = "", ""; all_name_divs = header_div.find_all('div', class_='itemName')
                    for div in all_name_divs:
                        classes, lc_span = div.get('class', []), div.find('span', class_='lc')
                        if lc_span:
                            if 'typeLine' in classes: base_type = lc_span.text.strip()
                            else: item_name_exclusive = lc_span.text.strip()
                    item_data['BaseType'] = base_type
                    item_data['ItemName'] = f"{item_name_exclusive} {base_type}".strip() if item_name_exclusive else base_type
                
                # 智能解析content区域
                content_div = middle_pane.find('div', class_='content')
                if content_div:
                    # 优先找到ItemCategory
                    category_prop = content_div.find('div', class_='property'); item_data['ItemCategory'] = category_prop.text.strip() if category_prop else 'Unknown'

                    # 【最终修正】解析技能
                    skills_div = content_div.find('div', class_='skills')
                    if skills_div:
                        skill_property_div = skills_div.find('div', class_='property skill')
                        if skill_property_div:
                            property_skill_span = skill_property_div.find_all('span',class_='lc s')
                            if property_skill_span:
                                last_span = property_skill_span[-1]
                                item_data['GrantedSkill'] = last_span.text.strip()

                    
                    # 解析需求和物品等级
                    req_div = content_div.find('div', class_='requirements')
                    if req_div:
                        req_text = req_div.text.strip().replace('Requires', '')
                        lvl_match = re.search(r'Level\s*(\d+)', req_text); item_data['RequiredLevel'] = int(lvl_match.group(1)) if lvl_match else None
                        str_match = re.search(r'(\d+)\s*Str', req_text); item_data['RequiredStr'] = int(str_match.group(1)) if str_match else None
                        dex_match = re.search(r'(\d+)\s*Dex', req_text); item_data['RequiredDex'] = int(dex_match.group(1)) if dex_match else None
                        int_match = re.search(r'(\d+)\s*Int', req_text); item_data['RequiredInt'] = int(int_match.group(1)) if int_match else None
                    ilvl_div = content_div.find('div', class_='itemLevel')
                    if ilvl_div: item_data['ItemLevel'] = int(ilvl_div.text.replace('Item Level:', '').strip())

                    # 遍历解析所有property
                    for prop in content_div.find_all('div', class_='property'):
                        prop_text = prop.text.strip()
                        # 公共属性
                        if 'Quality:' in prop_text: item_data['Quality'] = int(re.search(r'\d+', prop_text).group())
                        # 武器属性
                        elif 'Physical Damage:' in prop_text: dmg = [int(p) for p in re.findall(r'\d+', prop_text)]; weapon_props['PhysicalDmgMin'], weapon_props['PhysicalDmgMax'] = (dmg[0], dmg[1]) if len(dmg) > 1 else (dmg[0], dmg[0])
                        elif 'Cold Damage:' in prop_text: dmg = [int(p) for p in re.findall(r'\d+', prop_text)]; weapon_props['ColdDmgMin'], weapon_props['ColdDmgMax'] = (dmg[0], dmg[1]) if len(dmg) > 1 else (dmg[0], dmg[0])
                        elif 'Fire Damage:' in prop_text: dmg = [int(p) for p in re.findall(r'\d+', prop_text)]; weapon_props['FireDmgMin'], weapon_props['FireDmgMax'] = (dmg[0], dmg[1]) if len(dmg) > 1 else (dmg[0], dmg[0])
                        elif 'Lightning Damage:' in prop_text: dmg = [int(p) for p in re.findall(r'\d+', prop_text)]; weapon_props['LightningDmgMin'], weapon_props['LightningDmgMax'] = (dmg[0], dmg[1]) if len(dmg) > 1 else (dmg[0], dmg[0])
                        elif 'Chaos Damage:' in prop_text: dmg = [int(p) for p in re.findall(r'\d+', prop_text)]; weapon_props['ChaosDmgMin'], weapon_props['ChaosDmgMax'] = (dmg[0], dmg[1]) if len(dmg) > 1 else (dmg[0], dmg[0])
                        elif 'Critical Hit Chance:' in prop_text: weapon_props['CritChance'] = float(re.search(r'[\d.]+', prop_text).group())
                        elif 'Attacks per Second:' in prop_text: weapon_props['AttacksPerSecond'] = float(re.search(r'[\d.]+', prop_text).group())
                        # 护甲属性
                        elif 'Armour:' in prop_text: armor_props['Armour'] = int(re.search(r'\d+', prop_text).group())
                        elif 'Evasion Rating:' in prop_text: armor_props['Evasion'] = int(re.search(r'\d+', prop_text).group())
                        elif 'Energy Shield:' in prop_text: armor_props['EnergyShield'] = int(re.search(r'\d+', prop_text).group())
                        # 盾牌属性
                        elif 'Block chance:' in prop_text: shield_props['BlockChance'] = float(re.search(r'[\d.]+', prop_text).group())
                        # 【新增】Reload Time
                        elif 'Reload Time:' in prop_text: weapon_props['ReloadTime'] = float(re.search(r'[\d.]+', prop_text).group())
                        # 【新增】Spirit
                        elif 'Spirit:' in prop_text: weapon_props['Spirit'] = int(re.search(r'\d+', prop_text).group())

                    # 遍历解析所有词缀
                    for mod in content_div.find_all('div', recursive=False):
                        class_list = mod.get('class', [])
                        mod_text = mod.text.strip().replace('\xa0', ' ')
                        if 'implicitMod' in class_list: affixes.append({'text': mod_text, 'type': 'Implicit'})
                        elif 'explicitMod' in class_list: affixes.append({'text': mod_text, 'type': 'Explicit'})
                        elif 'enchantMod' in class_list: affixes.append({'text': mod_text, 'type': 'Enchant'}); item_data['IsCorrupted'] = 1
                        # ... etc for rune, corrupted ...
            # --- 【关键】数据入库 (适配新架构) ---
            
            # 1. 处理外键：Users 和 Currencies (逻辑不变)
            seller_name = item_data.get('SellerName', 'Unknown')
            cursor.execute("SELECT UserID FROM Users WHERE UserName = ?", seller_name)
            user_row = cursor.fetchone()
            user_id = user_row[0] if user_row else cursor.execute("INSERT INTO Users (UserName) OUTPUT INSERTED.UserID VALUES (?)", seller_name).fetchone()[0]

            currency_name = item_data.get('CurrencyName', 'N/A')
            cursor.execute("SELECT CurrencyID FROM Currencies WHERE CurrencyName = ?", currency_name)
            currency_row = cursor.fetchone()
            currency_id = currency_row[0] if currency_row else cursor.execute("INSERT INTO Currencies (CurrencyName) OUTPUT INSERTED.CurrencyID VALUES (?)", currency_name).fetchone()[0]
            
            # 2. 【新增】处理外键：ItemCategories
            category_name = item_data.get('ItemCategory', 'Unknown')
            cursor.execute("SELECT CategoryID FROM ItemCategories WHERE CategoryName = ?", category_name)
            category_row = cursor.fetchone()
            category_id = category_row[0] if category_row else cursor.execute("INSERT INTO ItemCategories (CategoryName) OUTPUT INSERTED.CategoryID VALUES (?)", category_name).fetchone()[0]

            # 3. 【新增】处理外键：Skills
            skill_name = item_data.get('GrantedSkill')
            skill_id = None # 默认为NULL
            if skill_name: # 只有在提取到技能名时才处理
                cursor.execute("SELECT SkillID FROM Skills WHERE SkillName = ?", skill_name)
                skill_row = cursor.fetchone()
                skill_id = skill_row[0] if skill_row else cursor.execute("INSERT INTO Skills (SkillName) OUTPUT INSERTED.SkillID VALUES (?)", skill_name).fetchone()[0]

            # 4. 插入或更新 Items 公共表 (使用新的外键ID)
            if not cursor.execute("SELECT 1 FROM Items WHERE ItemID = ?", item_id).fetchone():
                cols = ("ItemID, ItemName, BaseType, ItemImageURL, Quality, IsCorrupted, "
                        "ItemLevel, RequiredLevel, RequiredStr, RequiredDex, RequiredInt, "
                        "PriceAmount, ListedAtText, UserID, CurrencyID, "
                        "CategoryID, SkillID") # <-- 使用新的ID列
                
                vals = "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?" # 17个问号
                
                params = (
                    item_id, item_data.get('ItemName'), item_data.get('BaseType'), 
                    item_data.get('ItemImageURL'), item_data.get('Quality', 0), item_data.get('IsCorrupted', 0), 
                    item_data.get('ItemLevel'), item_data.get('RequiredLevel'), 
                    item_data.get('RequiredStr'), item_data.get('RequiredDex'), item_data.get('RequiredInt'),
                    item_data.get('PriceAmount', 0), item_data.get('ListedAtText'), 
                    user_id, currency_id, category_id, skill_id # <-- 传入新的ID
                )
                cursor.execute(f"INSERT INTO Items ({cols}) VALUES ({vals})", params)

            # 5. 插入扩展表 (逻辑不变)
            def upsert_extension_table(table_name, props_dict):
                if props_dict and not cursor.execute(f"SELECT 1 FROM {table_name} WHERE ItemID = ?", item_id).fetchone():
                    cols = "ItemID, " + ", ".join(props_dict.keys())
                    vals = "?, " + ", ".join(["?"] * len(props_dict))
                    params = (item_id, *props_dict.values())
                    cursor.execute(f"INSERT INTO {table_name} ({cols}) VALUES ({vals})", params)
            
            upsert_extension_table('WeaponProperties', weapon_props)
            upsert_extension_table('ArmorProperties', armor_props)
            upsert_extension_table('ShieldProperties', shield_props)
            
            # 6. 插入词缀 (逻辑不变)
            cursor.execute("DELETE FROM Affixes WHERE ItemID = ?", item_id)
            for affix in affixes:
                cursor.execute("INSERT INTO Affixes (ItemID, AffixText, AffixType) VALUES (?, ?, ?)", item_id, affix['text'], affix['type'])

            conn.commit()
            print(f"  -> [成功] 物品 '{item_data.get('ItemName')}' 已处理并存入新架构。")

        except Exception as e:
            print(f"  -> [错误] 处理物品ID {item_id if item_id else 'N/A'}... 时发生错误: {e}")
            conn.rollback()
            continue
            
    conn.close()
    print("\n本次批处理完成！")


# --------------------------------------------------------------------------
# 3. 主循环 (保持不变)
# --------------------------------------------------------------------------
# ... (这部分代码完全保持不变) ...
print("="*60); print(">>> 剪贴板监控器已启动！(大师最终版) <<<"); print("...")
last_content_hash, i = None, 0; waiting_animation = ['|', '/', '—', '\\']
try:
    while True:
        print(f"\r正在等待你复制HTML... {waiting_animation[i % 4]}", end=""); i += 1
        current_content = pyperclip.paste()
        if current_content and current_content.strip().startswith('<'):
            current_hash = hashlib.md5(current_content.encode('utf-8')).hexdigest()
            if current_hash != last_content_hash:
                print("\r" + " "*50 + "\r", end=""); parse_and_save_data(current_content)
                last_content_hash = current_hash; print("\n操作完成！继续等待下一次复制...")
        time.sleep(0.5)
except KeyboardInterrupt: print("\n程序已退出。")