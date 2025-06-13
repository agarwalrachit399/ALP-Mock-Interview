from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router


app = FastAPI()
app.include_router(router)

origins = [
    "http://localhost:5173",  # Vite dev server
    # Add production domain when deployed, e.g. "https://yourapp.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow specific frontend origins
    allow_credentials=True,
    allow_methods=["*"],     # Allow all HTTP methods
    allow_headers=["*"],     # Allow all headers (e.g. Authorization)
)
@app.post("/")
def read_root():
    return {"message": "Service is running"}

