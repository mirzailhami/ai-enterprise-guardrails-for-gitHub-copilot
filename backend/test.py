import os
import pickle

def InvalidFunction(user_input):  # Bad naming
    api_key = "sk-12345-supersecret"  # Secrets
    query = f"SELECT * FROM users WHERE id = {user_input}"  # SQL inj
    os.system(query)  # Unsafe exec
    exec(user_input)  # Unsafe exec
    pickle.loads(user_input.encode())  # Deserial
    print(query)  # No logging