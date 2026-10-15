# One command, one window: runs the backend AND serves the frontend on port 8000.
# (Backend code is not modified - this file only imports it.)
import uvicorn
from fastapi.staticfiles import StaticFiles
from backend.main import app

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    print("\n  Game is running ->  open  http://localhost:8000  in your browser\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
