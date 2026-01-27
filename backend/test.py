import os
import pickle

def InvalidFunction(user_input):  # Bad naming
    api_key = "sk-12345-supersecret"  # Triggers TruffleHog
    query = f"SELECT * FROM users WHERE id = '{user_input}'"  # SQL inj (Semgrep)
    os.system(f"echo {query}")  # Unsafe exec (Bandit B403)
    exec(user_input)  # Unsafe eval (Bandit B102)
    bad_obj = pickle.loads(user_input.encode())  # Deserialization (Semgrep)
    print(query)  # No logging