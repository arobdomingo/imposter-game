import asyncio
import logging
from fastapi import FastAPI, Depends, APIRouter
from sqlalchemy.orm import Session
from nicegui import ui

from user_service.models.friendship_routes import router as friendship_router


from user_service.models.user import (
    UserRepository,
    UserSchema,
    get_user_repository,
)
from shared.database import get_db

# ------------------ FASTAPI APP ------------------
app = FastAPI()
app.include_router(friendship_router)  # ✅ Register friendship routes

# ------------------ CONFIG ------------------
ADMIN_PASSWORD = "admin123"
logger = logging.getLogger("uvicorn.error")
router = APIRouter()

# ------------------ UI COMPONENTS ------------------
@ui.refreshable
async def user_list(user_repo: UserRepository, layout) -> list[str]:
    user_models = await user_repo.get_all()
    users = [UserSchema.from_db_model(model).model_dump() for model in user_models]

    with layout:
        ui.label("All Users")
        selected = []

        async def delete():
            nonlocal selected
            for user in selected:
                result = await user_repo.delete(user["name"])
                if result.rowcount > 0:
                    ui.notify(f"Deleted user '{user['name']}'")
                else:
                    ui.notify(f"Unable to delete user `{user['name']}'")
            await user_list(user_repo, layout)

        button = ui.button(on_click=delete, icon="delete")
        button.disable()

        def toggle_delete_button(e):
            nonlocal selected
            selected = e.selection
            button.enable() if selected else button.disable()

        columns = [{"name": "name", "label": "Name", "field": "name", "required": True, "align": "left"}]

        table = ui.table(columns=columns, rows=users, row_key="name", on_select=toggle_delete_button)
        table.set_selection("multiple")

    return [user["name"] for user in users]


async def show_admin_ui(user_repo: UserRepository, layout):
    with layout:
        async def create() -> None:
            await user_repo.create(name=name.value)
            name.value = ""
            await user_list(user_repo, layout)

        with ui.row().classes("w-full items-center px-4"):
            name = ui.input(label="Name")
            ui.button(on_click=create, icon="add")

        await user_list(user_repo, layout)


# ------------------ MAIN ADMIN PAGE ------------------
@ui.page("/")
async def admin_entry(user_repo: UserRepository = Depends(get_user_repository)):
    layout = ui.column().classes("mx-auto")
    with layout:
        ui.label("Admin Login").classes("text-xl")
        password_input = ui.input(label="Enter Admin Password", password=True)
        login_button = ui.button("Login")

    def try_login():
        if password_input.value == ADMIN_PASSWORD:
            ui.notify("Access granted")
            layout.clear()
            asyncio.create_task(show_admin_ui(user_repo, layout))
        else:
            ui.notify("Incorrect password", type="negative")

    login_button.on("click", try_login)


__all__ = ["router", "ui"]
