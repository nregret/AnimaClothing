#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
import hashlib
import random
import re

# 配置参数
JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "clothing_data.json"))
LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "translate_baidu.log"))
API_URL = "https://api.fanyi.baidu.com/api/trans/vip/translate"

# 百度翻译凭证
APP_ID = "20250601002371232"
SECRET_KEY = "OFDnEilblE0zb1lLvncI"

# 25 个特征词列表
TRAITS_LIST = [
    'apron', 'backless', 'bare legs', 'boots', 'collar', 'garter belt', 
    'glasses', 'gloves', 'halterneck', 'high heels', 'kneehighs', 'lace', 
    'latex', 'leather', 'miniskirt', 'off-shoulder', 'pantyhose', 'ribbon', 
    'short shorts', 'side slit', 'silk', 'sleeveless', 'thighhighs', 'tie', 
    'translucent'
]

# 特殊精细化汉化词典
SPECIAL_DICT = {
    "halterneck": "吊颈式设计 (挂颈式/肩带绕过颈部后方支撑支撑衣物)",
    "detached sleeves": "可拆卸袖套",
    "frilled sleeves": "荷叶边袖",
    "frills": "荷叶边/褶边",
    "white dress": "白色连衣裙",
    "white gloves": "白色手套",
    "white thighhighs": "白色大腿袜",
    "high heels": "高跟鞋",
    "bare arms": "无袖/裸臂",
    "bare shoulders": "露肩",
    "evening gown": "晚礼服",
    "side slit": "侧开叉",
    "pelvic curtain": "盆骨帘",
    "groin": "腹股沟",
    "revealing clothes": "暴露服饰",
    "bare legs": "光腿",
    "crystal footwear": "水晶鞋",
    "crop top": "露脐短上衣",
    "underbust": "露下乳 (衣服下摆仅到胸部下沿)",
    "thigh strap": "大腿绑带",
    "thighhighs": "大腿袜",
    "gloves": "手套",
    "dress": "连衣裙/礼服",
    "skirt": "半身裙",
    "bikini": "比基尼",
    "lingerie": "内衣",
    "stockings": "长筒袜",
    "garter belt": "吊袜带",
    "cleavage": "乳沟",
    "collar": "衣领",
    "ribbon": "丝带/蝴蝶结",
    "apron": "围裙",
    "boots": "靴子",
    "pantyhose": "连裤袜"
}

def log_print(msg):
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(msg + "\n")
    except:
        pass
    try:
        print(msg, flush=True)
    except:
        pass

def baidu_translate(text, from_lang='en', to_lang='zh'):
    salt = str(random.randint(32768, 65536))
    sign_src = APP_ID + text + salt + SECRET_KEY
    sign = hashlib.md5(sign_src.encode('utf-8')).hexdigest()
    
    payload = {
        'q': text,
        'from': from_lang,
        'to': to_lang,
        'appid': APP_ID,
        'salt': salt,
        'sign': sign
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    for attempt in range(3):
        try:
            response = requests.post(API_URL, data=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                if "error_code" in res_data:
                    err_code = res_data["error_code"]
                    err_msg = res_data.get("error_msg", "Unknown error")
                    log_print(f"  └─ 百度 API 返回错误 {err_code}: {err_msg}")
                    if err_code == "54003":  # 频率限制
                        time.sleep(1.5)
                        continue
                    return None
                trans_result = res_data.get("trans_result", [])
                if trans_result:
                    return "".join([item["dst"] for item in trans_result])
            else:
                log_print(f"  └─ 百度 API 状态码异常: {response.status_code}")
        except Exception as e:
            log_print(f"  └─ 百度 API 网络请求异常: {e}")
        time.sleep(1.0)
    return None

def translate_tags(tags_str):
    tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]
    special_indices = {}
    normal_tags = []
    normal_indices = []
    
    for idx, tag in enumerate(tags_list):
        tag_lower = tag.lower()
        matched = False
        for k, v in SPECIAL_DICT.items():
            if k == tag_lower:
                special_indices[idx] = v
                matched = True
                break
        if not matched:
            normal_tags.append(tag)
            normal_indices.append(idx)
            
    if not normal_tags:
        result_tags = [special_indices[i] for i in range(len(tags_list))]
        return ", ".join(result_tags)
        
    lines_query = [f"{i+1}. {t}" for i, t in enumerate(normal_tags)]
    query_text = "\n".join(lines_query)
    translated_text = baidu_translate(query_text)
    time.sleep(1.0)
    
    translated_normals = []
    if translated_text:
        lines = [t.strip() for t in translated_text.split('\n') if t.strip()]
        for line in lines:
            clean_line = re.sub(r'^\d+[\.\s、]+', '', line).strip()
            translated_normals.append(clean_line)
        
    if len(translated_normals) != len(normal_tags):
        log_print(f"  └─ [降级] 批量翻译行数不匹配，改为逐个翻译...")
        translated_normals = []
        for tag in normal_tags:
            trans = baidu_translate(tag)
            time.sleep(1.0)
            translated_normals.append(trans if trans else tag)
            
    result_tags = [None] * len(tags_list)
    for idx, val in special_indices.items():
        result_tags[idx] = val
    for i, idx in enumerate(normal_indices):
        result_tags[idx] = translated_normals[i] if i < len(translated_normals) else normal_tags[i]
        
    return ", ".join(result_tags)

def build_categories(tags_str):
    categories = []
    tags_lower = [t.strip().lower() for t in tags_str.split(",") if t.strip()]
    
    # 角色扮演/奇幻 (Fantasy & Cosplay)
    fantasy_keywords = ["miko", "kimono", "cosplay", "ninja", "taimanin", "witch", "demon", "angel", "armor", "elf", "fairy", "succubus", "horns", "wings"]
    if any(kw in tags_lower or any(kw in t for t in tags_lower) for kw in fantasy_keywords):
        categories.append("角色扮演/奇幻 (Fantasy & Cosplay)")
        
    # 性感/暴露 (Revealing)
    revealing_keywords = ["revealing", "naked", "topless", "bottomless", "sideboob", "underboob", "cleavage", "panties", "thong", "cameltoe", "no panties", "sideless", "bareback", "exposed", "pasties"]
    if any(kw in tags_lower or any(kw in t for t in tags_lower) for kw in revealing_keywords):
        categories.append("性感/暴露 (Revealing)")
        
    # 泳装/内衣 (Swimsuit & Lingerie)
    swimsuit_keywords = ["bikini", "swimsuit", "leotard", "bodysuit", "lingerie", "bra", "panties", "stockings", "pantyhose", "thighhighs", "garter", "legwear"]
    if any(kw in tags_lower or any(kw in t for t in tags_lower) for kw in swimsuit_keywords):
        categories.append("泳装/内衣 (Swimsuit & Lingerie)")
        
    # 制服/西服 (Uniform & Suit)
    uniform_keywords = ["uniform", "suit", "police", "maid", "nurse", "school uniform", "serafuku", "blazer", "apron", "waitress", "stewardess"]
    if any(kw in tags_lower or any(kw in t for t in tags_lower) for kw in uniform_keywords):
        categories.append("制服/西服 (Uniform & Suit)")
        
    # 礼服/裙装 (Dress & Gown)
    dress_keywords = ["dress", "gown", "skirt", "evening gown", "cheongsam", "hanfu", "sundress"]
    if any(kw in tags_lower or any(kw in t for t in tags_lower) for kw in dress_keywords):
        categories.append("礼服/裙装 (Dress & Gown)")
        
    if not categories:
        categories.append("日常/休闲 (Casual & Daily)")
        
    return categories

def build_traits(tags_str):
    tags_lower = [t.strip().lower() for t in tags_str.split(",") if t.strip()]
    traits = []
    for trait in TRAITS_LIST:
        if any(trait == t or re.search(r'\b' + re.escape(trait) + r'\b', t) for t in tags_lower):
            traits.append(trait)
    return traits

def generate_name(tags_str):
    tags_list = [t.strip() for t in tags_str.split(",") if t.strip()]
    if not tags_list:
        return "Unknown Outfit"
    
    name_parts = tags_list[:2]
    formatted_parts = [t.title() for t in name_parts]
    return " & ".join(formatted_parts)

def main():
    owner = "hayde0096"
    repo = "Kisegaeningyou"
    
    log_print(f"正在读取本地数据库: {JSON_PATH}")
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            clothing_data = json.load(f)
    else:
        clothing_data = []
        
    existing_ids = {item["id"] for item in clothing_data}
    log_print(f"本地已有 ID 数量: {len(existing_ids)}")
    
    print("正在请求官方 GitHub 仓库 images5 列表...")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/images5"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            log_print(f"请求 images5 列表失败: {r.status_code}")
            return
        files = r.json()
    except Exception as e:
        log_print(f"请求异常: {e}")
        return
        
    img_files = [f for f in files if f["name"].lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    log_print(f"官方 images5 包含图片共: {len(img_files)} 张")
    
    new_added = 0
    
    for idx, f in enumerate(img_files):
        filename = f["name"]
        photo_id = os.path.splitext(filename)[0]
        
        if photo_id in existing_ids:
            local_item = next((item for item in clothing_data if item["id"] == photo_id), None)
            if local_item and local_item.get("name_zh") and local_item.get("tags_zh"):
                continue
            if not local_item:
                continue
            log_print(f"[{idx+1}/{len(img_files)}] 补充汉化 ID: {photo_id}...")
        else:
            log_print(f"[{idx+1}/{len(img_files)}] 发现新服装 ID: {photo_id}...")
            
        desc_name = f"{filename}.desc.txt"
        desc_file = next((x for x in files if x["name"] == desc_name), None)
        
        tags = ""
        if desc_file:
            try:
                rd = requests.get(desc_file["download_url"], headers=headers, timeout=10)
                if rd.status_code == 200:
                    tags = rd.text.strip()
            except Exception as e:
                log_print(f"  └─ 获取描述文件失败: {e}")
                
        if not tags:
            log_print(f"  └─ 警告: tags 为空，跳过。")
            continue
            
        name = generate_name(tags)
        preview = f"https://cdn.jsdelivr.net/gh/{owner}/{repo}@main/images5/{filename}"
        categories = build_categories(tags)
        traits = build_traits(tags)
        
        log_print(f"  ├─ Name: {name}")
        log_print(f"  ├─ Categories: {categories}")
        log_print(f"  ├─ Traits: {traits}")
        
        log_print(f"  ├─ 正在调用百度 API 进行翻译...")
        name_zh = baidu_translate(name)
        time.sleep(1.0)
        tags_zh = translate_tags(tags)
        
        if name_zh and tags_zh:
            name_zh_clean = name_zh.strip()
            tags_zh_clean = tags_zh.strip()
            log_print(f"  ├─ 成功: {name_zh_clean}")
            log_print(f"  └─ Tags_zh: {tags_zh_clean}")
            
            if photo_id in existing_ids:
                local_item = next((item for item in clothing_data if item["id"] == photo_id), None)
                if local_item:
                    local_item["name_zh"] = name_zh_clean
                    local_item["tags_zh"] = tags_zh_clean
            else:
                new_item = {
                    "id": photo_id,
                    "name": name,
                    "preview": preview,
                    "tags": tags,
                    "categories": categories,
                    "traits": traits,
                    "folder": "images5",
                    "name_zh": name_zh_clean,
                    "tags_zh": tags_zh_clean
                }
                clothing_data.append(new_item)
                new_added += 1
                
            with open(JSON_PATH, 'w', encoding='utf-8') as save_file:
                json.dump(clothing_data, save_file, ensure_ascii=False, indent=2)
        else:
            log_print(f"  └─ 失败: 翻译未成功获取，本条跳过。")
            
        time.sleep(0.5)
        
    log_print(f"\n官方画廊五同步并翻译完毕！本次成功新增 {new_added} 条服装卡片。")

if __name__ == "__main__":
    main()
