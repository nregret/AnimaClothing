#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import requests
import re

## 配置参数
JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "clothing_data.json"))
BACKUP_PATH = JSON_PATH + ".bak"
API_URL = "http://localhost:1234/v1/chat/completions"
LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "translate.log"))

# 内置常用二次元/时尚服装词汇对照词典（当本地 LLM 超时或出错时的降级手段）
FALLBACK_DICT = {
    "halterneck": "吊颈式设计 (挂颈式/肩带绕过颈部后方支撑)",
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
    except Exception as e:
        pass
        
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        try:
            # Windows GBK 终端容错
            print(msg.encode('gbk', errors='ignore').decode('gbk'), flush=True)
        except:
            try:
                print(msg.encode('ascii', errors='ignore').decode('ascii'), flush=True)
            except:
                pass

def fallback_translate(name, tags):
    # 翻译 tags
    tags_list = [t.strip() for t in tags.split(',') if t.strip()]
    translated_tags = []
    for tag in tags_list:
        matched = False
        # 匹配词典
        for k, v in FALLBACK_DICT.items():
            if k in tag.lower():
                translated_tags.append(v)
                matched = True
                break
        if not matched:
            translated_tags.append(tag) # 匹配不到保留英文
            
    tags_zh = ", ".join(translated_tags)
    
    # 翻译 name
    name_zh = name
    for k, v in FALLBACK_DICT.items():
        if k in name.lower():
            name_zh = name_zh.lower().replace(k, v)
            
    # 格式化
    name_zh = name_zh.replace("&", "与").title()
    return name_zh, tags_zh

# 设定专业提示词
SYSTEM_PROMPT = """你是一个专业的时尚服装设计专家、买手、同时精通 AI 绘图（Stable Diffusion / NovelAI / Midjourney）的 Prompt 汉化。
你的任务是将英文服装名称和一串用逗号分隔的英文 tags 翻译成地道、贴合现实时尚设计、生动的中文。

翻译核心准则：
1. 拒绝机械的英文单词直译！翻译要贴合现实生活中的服装、时尚、潮流设计用语。
2. 比如 'halterneck' 绝对不要直译成“挂脖”，而应当翻译为“吊颈式”或“挂颈式”设计。
3. 如果某些专业词汇（特别是动漫/AI绘画中特有的服装Tag）对于普通用户而言较难理解、容易产生歧义或难以直译，请翻译出最贴切的意思，并在括号中附加一小段简单直白的原理或效果备注。
   例如：
   - halterneck ➔ 吊颈式 (挂颈式/肩带绕过颈后支撑衣物)
   - detached sleeves ➔ 可拆卸袖套
   - underbust ➔ 露下乳 (衣服下摆仅到胸部下沿)
   - crop top ➔ 露脐短上衣
   - pelvic curtain ➔ 盆骨帘
   - bare legs ➔ 光腿 (光溜的大腿)
   - thigh strap ➔ 大腿绑带
   - thighhighs ➔ 过膝大腿袜
4. 'name' 通常由核心款式组成，请把 'name' 翻译为一个优雅、自然、现实中时尚品牌会使用的服装中文名字（如 'Evening Gown & Halterneck' ➔ '吊颈式晚礼服'，而不是机械直译）。
5. 'tags' 请保持原来的逗号分隔形式输出，每一项翻译要一一对应。

你必须严格输出为标准的 JSON 格式，如下所示，不要包含任何 markdown 代码块标识、前导语或总结解释，只输出 JSON 本身：
{
  "name_zh": "中文服装名称",
  "tags_zh": "中文标签1, 中文标签2, 中文标签3"
}
"""

def get_translation(name, tags, force_fallback=False):
    if force_fallback:
        name_zh, tags_zh = fallback_translate(name, tags)
        return name_zh, tags_zh, True
        
    payload = {
        "model": "local-model", 
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Please translate this outfit:\nName: {name}\nTags: {tags}"}
        ],
        "temperature": 0.1
    }
    
    content = ""
    try:
        # 增加超时限制到 60 秒，防首次冷启动或者本地 CPU 推理慢
        response = requests.post(API_URL, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                json_str = match.group(0)
            else:
                json_str = content
                
            data = json.loads(json_str)
            return data.get("name_zh"), data.get("tags_zh"), False
        else:
            log_print(f"API 响应错误: 状态码 {response.status_code}, 内容: {response.text}")
    except Exception as e:
        log_print(f"请求本地大模型 API 发生异常: {e}. 响应内容: {content}")
        
    # 触发平滑降级：使用内置时尚小词典翻译
    name_zh, tags_zh = fallback_translate(name, tags)
    return name_zh, tags_zh, True


def main():
    import sys
    clean_mode = "--clean" in sys.argv
    
    # 清理上一次的日志
    if clean_mode and os.path.exists(LOG_PATH):
        try:
            os.remove(LOG_PATH)
        except:
            pass
            
    log_print(f"1. 检查数据文件: {JSON_PATH}")
    if not os.path.exists(JSON_PATH):
        log_print("错误: 找不到 clothing_data.json 文件！")
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
        log_print("检测到 --clean 参数，正在清空原有的旧版中文翻译...")
        for item in clothing_data:
            item.pop("name_zh", None)
            item.pop("tags_zh", None)
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(clothing_data, f, ensure_ascii=False, indent=2)
        log_print("原有中文翻译已清空！将从头开始由大模型翻译。")
        
    total = len(clothing_data)
    # 支持有些只有 tags_zh 没有 name_zh 或者都为 None 的进行检查
    translated_count = sum(1 for item in clothing_data if item.get("name_zh") and item.get("tags_zh"))
    log_print(f"当前总数据量: {total} 条，已完成翻译: {translated_count} 条，剩余待翻译: {total - translated_count} 条")
    
    if translated_count == total:
        log_print("所有数据已经全部翻译完成，无需重复执行！（如需重新翻译，请运行: python scripts/translate_with_local_llm.py --clean）")
        return
        
    success_in_this_run = 0
    consecutive_failures = 0
    
    for idx, item in enumerate(clothing_data):
        # 如果已经有 name_zh，且有 tags_zh，跳过（断点续传）
        if item.get("name_zh") and item.get("tags_zh"):
            continue
            
        # 熔断机制：如果连续 3 次超时失败，开启快速降级，直接用离线字典
        force_fallback = consecutive_failures >= 3
        if force_fallback and consecutive_failures == 3:
            log_print("\n⚠️ 警告: 检测到本地大模型连续超时已达 3 次，可能运行过于缓慢或未开启 GPU 加速。")
            log_print("⚠️ 为防卡死，已自动开启【快速熔断机制】，剩余所有数据将直接采用内置二次元服装词典快速翻译！\n")
            consecutive_failures += 1 # 累加，防止重复打印这一句警告
            
        log_print(f"[{idx+1}/{total}] 正在翻译 ID: {item['id']} ({item['name']})...")
        
        # 调用大模型翻译（带降级检测与熔断）
        name_zh, tags_zh, is_fallback = get_translation(item['name'], item['tags'], force_fallback=(force_fallback or consecutive_failures > 3))
        
        if name_zh and tags_zh:
            item["name_zh"] = name_zh.strip()
            item["tags_zh"] = tags_zh.strip()
            success_in_this_run += 1
            
            if force_fallback or consecutive_failures > 3:
                tag_type = "[快速熔断]"
            else:
                tag_type = "[降级词典]" if is_fallback else "[本地LLM]"
                
            log_print(f"  └─ {tag_type} 成功: {item['name_zh']} | Tags: {item['tags_zh']}")
            
            # 失败计数器累加或清零
            if is_fallback and not force_fallback:
                consecutive_failures += 1
            elif not is_fallback:
                consecutive_failures = 0 # 只要 LLM 成功了一次，就重置失败数
            
            # 实时保存到本地文件，确保断点续传稳健
            with open(JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(clothing_data, f, ensure_ascii=False, indent=2)
        else:
            log_print(f"  └─ 失败: 无法获取翻译，等待重试。")
            time.sleep(1)
            
        # 频率限制：如果已经进入熔断状态，则直接毫秒级刷完，不需要延迟
        if not force_fallback and consecutive_failures <= 3:
            time.sleep(0.1)
        
    log_print(f"\n处理完成！本轮成功翻译了 {success_in_this_run} 条数据。当前总进度: {sum(1 for item in clothing_data if item.get('name_zh') and item.get('tags_zh'))}/{total}")

if __name__ == "__main__":
    main()
