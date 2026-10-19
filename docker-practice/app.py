from pathlib import Path
from flask import Flask

''' comment'''
app = Flask(__name__)

COUNTER_FILE = Path("/data/count.txt")


def read_count():
    if COUNTER_FILE.exists():
        return int(COUNTER_FILE.read_text())
    return 0


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/count")
def get_count():
    return {"count": read_count()}


@app.post("/increment")
def increment():
    COUNTER_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    value = read_count() + 1
    COUNTER_FILE.write_text(str(value))

    return {"count": value}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)

