from fastapi import FastAPI
from auth_service.app.api.routes import router as auth_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Auth Service")
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
app.include_router(auth_router, prefix="/auth")
