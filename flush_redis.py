import subprocess, time

candidates = [f'C{str(i).zfill(3)}' for i in range(1, 21)]
for c in candidates:
    print(f'Deleting stale keys for {c}...')
    subprocess.run(['python', '-c', f'''
import redis, os
from dotenv import load_dotenv
load_dotenv()
r = redis.from_url(os.getenv("REDIS_URL","redis://localhost:6379"), decode_responses=True)
keys = r.keys("parsed_profile:{c}:*") + r.keys("ats_score:{c}:*")
for k in keys:
    r.delete(k)
print("Deleted", len(keys), "keys for {c}")
'''])

print("All stale keys deleted. Ready to re-parse.")
