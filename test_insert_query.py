import requests
import json

# Get token
login_url = 'http://localhost:5001/api/auth/login'
login_data = {'username': 'admin', 'password': 'admin123'}
login_response = requests.post(login_url, json=login_data, timeout=10)
token = login_response.json()['token']

# Now use the token to query
query_url = 'http://localhost:5001/api/chat/query'
query_data = {
    'message': 'create a new customer account with the name John Goodman, phone number 2347983838383',
    'conversation_id': 'test'
}
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
}

try:
    print("Sending request to chat/query endpoint...")
    response = requests.post(query_url, json=query_data, headers=headers, timeout=15)
    print(f'Status: {response.status_code}\n')
    result = response.json()
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
