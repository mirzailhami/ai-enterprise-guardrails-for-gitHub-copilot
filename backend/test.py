# test.py - Full violation test file for guardrails scanner
# For testing: commit with message containing "copilot" to trigger Copilot mode

import os
import pickle

# Potential IP/proprietary comment (should trigger ip_risk if keyword match)
# confidential proprietary code - all rights reserved

def BadCamelCaseFunction():  # violates naming "^[a-z_]+$"
    print("No logging import here - this should trigger logging violation")

def invalid_function(user_input):  # bad naming (but lowercase - adjust pattern if needed)
    api_key = "sk-12345-supersecret"           # hardcoded secret (secrets regex)
    query = f"SELECT * FROM users WHERE id = {user_input}"  # sql_injection via f-string
    os.system(query)                            # unsafe_exec regex (os.system)
    exec(user_input)                            # unsafe_exec AST (exec call)
    pickle.loads(user_input.encode())           # insecure_deserial AST
    print(query)                                # logging missing (no import logging)
    print("No logging here either")
    
def invalid_function(user_input):  # duplicate function definition
    print("Duplicate function - should trigger duplicate_code if within-file check enabled")

# Extra bad practice for AI review to catch
def another_bad_func():
    user_data = input("Enter data: ")  # no input validation
    eval(user_data)                    # dangerous eval
    print("Missing hyphen -")          # formatting issue for AI