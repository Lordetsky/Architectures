import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"

def make_request(method, path, data=None, headers=None):
    if headers is None:
        headers = {}
    
    url = BASE_URL + path
    body = None
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
        
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            response_body = response.read().decode('utf-8')
            print(f"[{method}] {path} - Status: {status}")
            print(f"Response: {response_body}\n")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"[{method}] {path} - FAILED with status: {e.code}")
        print(f"Error details: {error_body}\n")
    except Exception as e:
        print(f"[{method}] {path} - Exception: {str(e)}\n")

print("--- Начинаем тестирование API ---\n")

# Создание товара
make_request('POST', '/products', data={
    "name": "Sony PlayStation 5",
    "description": "Игровая приставка",
    "price": 500.0,
    "stock": 10,
    "category": "electronics",
    "status": "ACTIVE"
})

# Получение списка товаров
make_request('GET', '/products')

print("--- Тестирование завершено ---")
