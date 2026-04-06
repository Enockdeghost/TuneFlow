import re

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    return len(password) >= 8 and re.search(r'[A-Za-z]', password) and re.search(r'[0-9]', password)

def validate_username(username):
    return 3 <= len(username) <= 30 and re.match(r'^[a-zA-Z0-9_]+$', username)