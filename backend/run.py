#!/usr/bin/env python
from dotenv import load_dotenv
import os
import uvicorn

load_dotenv()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)