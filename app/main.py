# app/main.py

from fastapi import FastAPI

# نام این متغیر باید دقیقاً app باشد
app = FastAPI(title="Industrial Lathe Tools API")

@app.get("/")
async def root():
    return {"message": "API is running"}