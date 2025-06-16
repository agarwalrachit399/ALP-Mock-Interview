from fastapi import FastAPI
from app.api import routes
import asyncio
from contextlib import asynccontextmanager

# Background cleanup task
async def periodic_cleanup():
    """Periodically clean up expired sessions"""
    while True:
        try:
            # Clean up expired sessions every 30 minutes
            await asyncio.sleep(3600)  # 30 minutes
            
            # Call the cleanup endpoint
            import requests
            response = requests.post("http://localhost:8000/cleanup-expired", timeout=10)
            if response.status_code == 200:
                print("🧹 [BACKGROUND] Periodic cleanup completed")
            else:
                print("⚠️ [BACKGROUND] Periodic cleanup failed")
        except Exception as e:
            print(f"⚠️ [BACKGROUND] Cleanup task error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    print("🧹 [STARTUP] Background cleanup task started")
    
    yield
    
    # Cleanup on shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    print("🧹 [SHUTDOWN] Background cleanup task stopped")

app = FastAPI(lifespan=lifespan)
app.include_router(routes.router)