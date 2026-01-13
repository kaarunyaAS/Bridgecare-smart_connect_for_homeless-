from dotenv import load_dotenv, find_dotenv
import os
import pathlib

# Find the nearest .env (checks parent directories) and load it
env_path = pathlib.Path(__file__).parent / ".env"
if not env_path.exists():
	# fallback to find_dotenv which searches upward from cwd
	env_file = find_dotenv()
	if env_file:
		load_dotenv(env_file)
else:
	load_dotenv(dotenv_path=env_path)

# Print the expected environment variables by name
print("URL:", os.getenv("SUPABASE_URL"))
print("KEY:", os.getenv("SUPABASE_KEY"))
print("SECRET:", os.getenv("FLASK_SECRET_KEY"))
