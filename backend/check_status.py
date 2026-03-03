import urllib.request, json
from collections import defaultdict

d = json.loads(urllib.request.urlopen("http://127.0.0.1:8000/api/status", timeout=5).read())

groups = d.get("passenger_groups", [])
print(f"Active groups in memory: {len(groups)}")
print(f"Pending elevator requests: {d.get('pending_requests', 0)}")
print()

if not groups:
    print("No passenger groups currently in memory.")
    print("(This means all groups were delivered AND cleaned up — good sign!)")
else:
    print(f"{'Group ID':<45} {'State':<18} {'Wait':>5} {'Ride':>5} {'Del':>5} {'Tot':>5}")
    print("-" * 85)
    for g in sorted(groups, key=lambda x: x["id"]):
        print(f"{g['id']:<45} {g['state']:<18} {g['waiting_count']:>5} {g['riding_count']:>5} {g['delivered_count']:>5} {g['total_count']:>5}")

print()
elevators = d.get("elevators", [])
print("Elevator states:")
for e in elevators:
    print(f"  Elevator {e['id']} ({e['name']}): floor={e['current_floor']} status={e['status']} pax={e['passenger_count']}/{e['capacity']} queue={e.get('floor_queue', [])}")
