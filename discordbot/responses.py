import random
import os

def get_response(user_input: str) -> str:
    p_message:str = user_input.lower()
    
    if p_message == '':
        return 'No Message found...'
    elif p_message == 'hello':
        return 'Hey there!'        
    elif p_message == 'roll':
        return str(random.randint(1,6))
    elif p_message == '!help':
        return "`This is a help message that you can modify.`"
    else:
        return random.choice(['I do not understand...','What do you mean?'])
