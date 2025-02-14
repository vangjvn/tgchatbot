import requests
from config import settings
def test_proxy():
    try:
        proxies = {
            'http': settings.PROXY_URL,
            'https': settings.PROXY_URL
        }
        response = requests.get('https://api.telegram.org', proxies=proxies, timeout=10)
        print(f"代理测试成功: {response.status_code}")
    except Exception as e:
        print(f"代理测试失败: {str(e)}")

if __name__ == '__main__':
    test_proxy()