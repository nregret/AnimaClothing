import hashlib
import random
import requests

APP_ID = "20250601002371232"
SECRET_KEY = "OFDnEilblE0zb1lLvncI"
API_URL = "https://api.fanyi.baidu.com/api/trans/vip/translate"

def test():
    # 测试带句号多行 tags 批量翻译
    normal_tags = ["evening gown", "side slit", "pelvic curtain", "bare legs", "crystal footwear"]
    query_text = "\n".join([t + "." for t in normal_tags])
    
    salt = "1435660288"
    sign_src = APP_ID + query_text + salt + SECRET_KEY
    sign = hashlib.md5(sign_src.encode('utf-8')).hexdigest()
    
    payload = {
        'q': query_text,
        'from': 'en',
        'to': 'zh',
        'appid': APP_ID,
        'salt': salt,
        'sign': sign
    }
    
    try:
        response = requests.post(API_URL, data=payload, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        res_data = response.json()
        print("请求的多行原文:")
        print(query_text)
        print("\n百度响应原文:")
        trans_result = res_data.get("trans_result", [])
        for item in trans_result:
            print(f"{item['src']} -> {item['dst']}")
    except Exception as e:
        print(f"异常: {e}")

if __name__ == "__main__":
    test()
