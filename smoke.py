import time

import app as m

a = m.App()
deadline = time.time() + 30
while time.time() < deadline:
    a.update()
    if a.data is not None:
        break
    time.sleep(0.2)

print("busy:", a._busy)
print("status:", a.status.cget("text"))
print("statusbar:", a.statusbar.cget("text"))
print("data:", None if a.data is None else {
    "content": len(a.data["content"]),
    "polls": len(a.data["polls"]),
    "tallies": a.data.get("tallies"),
})

a.update()
a._on_close()
print("closed ok")
