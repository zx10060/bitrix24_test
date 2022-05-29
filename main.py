from dotenv import load_dotenv
from api import api
import uvicorn


load_dotenv()


if __name__ == "__main__":
    uvicorn.run(api.app, host="0.0.0.0", port=8000)
