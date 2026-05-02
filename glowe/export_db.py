import os
import subprocess
import sys

def export_data():
    try:
        # Set environment variable to force UTF-8 for the subprocess
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        with open('db_export.json', 'w', encoding='utf-8') as f:
            subprocess.run([
                sys.executable, 'manage.py', 'dumpdata', 
                '--exclude', 'contenttypes', 
                '--exclude', 'auth.Permission',
                '--exclude', 'socialaccount',
                '--exclude', 'account',
                '--exclude', 'sites',
                '--exclude', 'sessions',
                '--indent', '2'
            ], stdout=f, env=env, check=True)
        print("Data exported successfully to db_export.json")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    export_data()
