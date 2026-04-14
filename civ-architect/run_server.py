import sys
sys.path.insert(0, r'D:\kc\黑客松2\Civilization-Architect\civ-architect\lib')

from server import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
