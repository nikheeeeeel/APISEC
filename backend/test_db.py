import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    from registry_db import init_db, UserRegistry
    print("Testing init_db...")
    init_db()
    print("DB Init Successful.")
    
    print("Testing get_by_username...")
    usr = UserRegistry.get_by_username("test_user_diag")
    print("get_by_username Successful:", usr)
    
except Exception as e:
    import traceback
    traceback.print_exc()
