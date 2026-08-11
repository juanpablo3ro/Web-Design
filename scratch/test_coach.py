import requests

base_url = 'http://localhost:5001'

# Create a session to persist cookies (login session)
session = requests.Session()

# Log in
login_url = f'{base_url}/login'
login_data = {
    'email': 'sisi@gmail.com',
    'password': 'Juan_1256'
}

print("Attempting login...")
res = session.post(login_url, data=login_data)
if res.history:
    print(f"Logged in successfully. Redirected to {res.url}")
else:
    print(f"Failed to log in. Status code: {res.status_code}")
    exit(1)

# Test 1: init dialogue (greeting)
print("\nTesting init dialogue (Greeting)...")
dialogue_url = f'{base_url}/api/coach_avatar_dialogue'
init_payload = {
    'init': True
}
res_init = session.post(dialogue_url, json=init_payload)
print(f"Status code: {res_init.status_code}")
if res_init.ok:
    init_data = res_init.json()
    print("Greeting response from Ollama (prodi-diario:latest):")
    print(init_data.get('respuesta'))
else:
    print(f"Error: {res_init.text}")

# Test 2: sending a message (chat)
print("\nTesting chat message...")
message_payload = {
    'mensaje': '¿Cómo puedo reducir la sal en mis comidas?',
    'init': False
}
res_msg = session.post(dialogue_url, json=message_payload)
print(f"Status code: {res_msg.status_code}")
if res_msg.ok:
    msg_data = res_msg.json()
    print("Chat response from Ollama (prodi-diario:latest):")
    print(msg_data.get('respuesta'))
else:
    print(f"Error: {res_msg.text}")
