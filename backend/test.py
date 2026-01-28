import os
import pickle

def InvalidFunction(user_input):
    api_key = "sk-12345-supersecret"           # secrets regex
    query = f"SELECT * FROM users WHERE id = {user_input}"  # sql_injection
    os.system(query)                            # unsafe_exec regex
    exec(user_input)                            # unsafe_exec AST
    pickle.loads(user_input.encode())           # insecure_deserial AST
    print(query)                                # logging missing