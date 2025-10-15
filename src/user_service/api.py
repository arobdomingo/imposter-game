from fastapi import FastAPI
from user_service.models.user import Base
from shared.database import engine

# ✅ Auto-create tables
Base.metadata.create_all(bind=engine)

# ✅ Create FastAPI app
app = FastAPI()

# ✅ Mount NiceGUI admin dashboard
from admin.main import ui, router as admin_router
app.include_router(admin_router)
ui.run_with(app, mount_path="/admin", favicon="👤", title="User Admin")

# ✅ Include friendship routes
from user_service.models.friendship_routes import router as friendship_router
app.include_router(friendship_router)

