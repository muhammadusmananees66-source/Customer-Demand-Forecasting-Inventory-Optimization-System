import uvicorn
from src.serving.api import create_app

app = create_app({
    "model": {"model_path": "./models/test_run_id/model.pkl"},
})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
