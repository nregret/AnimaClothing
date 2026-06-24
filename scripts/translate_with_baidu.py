#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
import hashlib
import random
import urllib.parse
import sys
import re

# 配置参数
JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "clothing_data.json"))
BACKUP_PATH = JSON_PATH + ".bak"
LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "translate_baidu.log"))
API_URL = "https://api.fanyi.baidu.com/api/trans/vip/translate"

# 百度翻译凭证 (请将 APP_ID 替换为你自己的百度翻译 APP ID)
APP_ID = "YOUR_APP_ID"
SECRET_KEY = "OFDnEilblE0zb1lLvncI"

# 特殊精细化汉化词典（AI绘画及服装圈专业词汇，在此处的词汇将直接应用，不调用百度，确保翻译极贴合现实且带括号原理备注）
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
    except UnicodeEncodeError:
        try:
            print(msg.encode('gbk', errors='ignore').decode('gbk'), flush=True)
        except:
            pass

def baidu_translate(text, from_lang='en', to_lang='zh'):
    if not APP_ID or APP_ID == "YOUR_APP_ID":
        raise ValueError("未配置百度翻译 APP ID，请先在脚本中配置 APP_ID")
        
    salt = str(random.randint(32768, 65536))
    # 签名公式: md5(appid+q+salt+securityKey)
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
    
    # 失败重试 3 次
    for attempt in range(3):
        try:
            response = requests.post(API_URL, data=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                if "error_code" in res_data:
                    err_code = res_data["error_code"]
                    err_msg = res_data.get("error_msg", "Unknown error")
                    log_print(f"  └─ 百度 API 返回错误 {err_code}: {err_msg}")
                    if err_code == "54003": # 访问频率限制，多等一下再重试
                        time.sleep(1.5)
                        continue
                    return None
                
                # 拼接翻译结果
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
    
    # 区分特殊词和普通词
    special_indices = {} # 索引 -> 翻译值
    normal_tags = []
    normal_indices = [] # 记录普通词在原列表中的索引
    
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
            
    # 如果没有普通词需要翻译，直接拼装返回
    if not normal_tags:
        result_tags = [special_indices[i] for i in range(len(tags_list))]
        return ", ".join(result_tags)
        
    # 用换行符拼接普通词，并给每一行加上数字前缀（例如 1. tag），强制引导百度分句器按行翻译，确保 100% 对齐！
    lines_query = [f"{i+1}. {t}" for i, t in enumerate(normal_tags)]
    query_text = "\n".join(lines_query)
    translated_text = baidu_translate(query_text)
    time.sleep(1.0)
    
    translated_normals = []
    if translated_text:
        # 按行切分，保留完全对应的翻译行并正则剥离数字前缀
        lines = [t.strip() for t in translated_text.split('\n') if t.strip()]
        for line in lines:
            clean_line = line
            # 剥离类似 "1." 或 "1. " 或 "1、" 的数字前缀
            clean_line = re.sub(r'^\d+[\.\s、]+', '', clean_line).strip()
            translated_normals.append(clean_line)
        
    # 如果百度返回的行数不匹配，触发降级：逐个单词翻译或直接保留英文
    if len(translated_normals) != len(normal_tags):
        log_print(f"  └─ [降级] 批量翻译行数不匹配 (请求 {len(normal_tags)} 行，返回 {len(translated_normals)} 行)，改用逐个翻译...")
        translated_normals = []
        for tag in normal_tags:
            trans = baidu_translate(tag)
            time.sleep(1.0)
            translated_normals.append(trans if trans else tag)
            
    # 合并特殊词与普通词的翻译结果
    result_tags = [None] * len(tags_list)
    for idx, val in special_indices.items():
        result_tags[idx] = val
        
    for i, idx in enumerate(normal_indices):
        result_tags[idx] = translated_normals[i] if i < len(translated_normals) else normal_tags[i]
        
    return ", ".join(result_tags)

def main():
    global APP_ID
    
    # 支持从命令行参数传入 APP_ID，如 python scripts/translate_with_baidu.py 2015063000000001
    import sys
    clean_mode = "--clean" in sys.argv
    
    # 查找是否有参数是纯数字作为 APP_ID
    for arg in sys.argv[1:]:
        if arg.isdigit():
            APP_ID = arg
            break
            
    if clean_mode and os.path.exists(LOG_PATH):
        try:
            os.remove(LOG_PATH)
        except:
            pass

    log_print(f"1. 检查数据文件: {JSON_PATH}")
    if not os.path.exists(JSON_PATH):
        log_print("错误: 找不到 clothing_data.json 文件！")
        return
        
    if not APP_ID or APP_ID == "YOUR_APP_ID":
        log_print("❌ 错误: 未配置百度的 APP_ID！")
        log_print("请使用此格式运行命令: python scripts/translate_with_baidu.py <你的百度APP_ID> [--clean]")
        return
        
    # 自动备份
    if not os.path.exists(BACKUP_PATH):
        log_print(f"创建数据备份: {BACKUP_PATH}")
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = f.read()
        with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
            f.write(data)
            
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        clothing_data = json.load(f)
        
    if clean_mode:
        log_print("检测到 --clean 参数，正在清空之前翻译的中文字段...")
        for item in clothing_data:
            item.pop("name_zh", None)
            item.pop("tags_zh", None)
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(clothing_data, f, ensure_ascii=False, indent=2)
        log_print("历史翻译已清空！将使用百度翻译 API 重新汉化。")
        
    total = len(clothing_data)
    translated_count = sum(1 for item in clothing_data if item.get("name_zh") and item.get("tags_zh"))
    log_print(f"当前总数据量: {total} 条，已完成翻译: {translated_count} 条，剩余待翻译: {total - translated_count} 条")
    
    if translated_count == total:
        log_print("所有数据已经全部翻译完成，无需重复执行！")
        return
        
    success_in_this_run = 0
    
    for idx, item in enumerate(clothing_data):
        if item.get("name_zh") and item.get("tags_zh"):
            continue
            
        log_print(f"[{idx+1}/{total}] 正在翻译 ID: {item['id']} ({item['name']})...")
        
        # 1. 翻译服装名称
        name_zh = baidu_translate(item['name'])
        time.sleep(1.0)
        
        # 2. 翻译服装 tags (内部含词典优先和百度API后备)
        tags_zh = translate_tags(item['tags'])
        
        if name_zh and tags_zh:
            item["name_zh"] = name_zh.strip()
            item["tags_zh"] = tags_zh.strip()
            success_in_this_run += 1
            log_print(f"  └─ 成功: {item['name_zh']} | Tags: {item['tags_zh']}")
            
            # 实时保存，确保断点续传稳健
            with open(JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(clothing_data, f, ensure_ascii=False, indent=2)
        else:
            log_print(f"  └─ 失败: 无法获取百度 API 翻译结果，跳过或重试。")
            
        time.sleep(0.5)
        
    log_print(f"\n百度 API 翻译完成！本轮成功处理 {success_in_this_run} 条数据。当前总进度: {sum(1 for item in clothing_data if item.get('name_zh') and item.get('tags_zh'))}/{total}")

if __name__ == "__main__":
    main()
