import random
from fastapi import Depends
from nicegui import ui
from pydantic import parse_obj_as
from contextlib import contextmanager
import logging
import copy
from sqlalchemy.exc import IntegrityError


from user_service.models.user import UserRepository, UserSchema, get_user_repository


logger = logging.getLogger('uvicorn.error')

@ui.refreshable
async def user_list(user_repo: UserRepository) -> None:

    user_models = await user_repo.get_all()
    users = []
    for model in user_models:
        users.append(UserSchema.from_db_model(model).model_dump())

    ui.label("All Users")

    selected = []
    async def delete():
        global selected
        try:
            deleted_users = []
            for user in selected:
                result = await user_repo.delete(user['name'])
                if result.rowcount > 0:
                    deleted_users.append(user['name'])
                    ui.notify(f"Deleted user '{user['name']}'", type='positive')
                else:
                    ui.notify(f"Unable to delete user '{user['name']}'", type='negative')
            
            # Refresh the user list to show the updates
            user_list.refresh()
            
            # Clear selected state
            selected = []
            button.disable()
            
        except Exception as e:
            ui.notify(f"Error deleting users: {str(e)}", type='negative')
            user_list.refresh()
            selected = []
            button.disable()

    button = ui.button(on_click=delete, icon='delete')

    button.disable()
    def toggle_delete_button(e):
        global selected
        selected = e.selection
        if len(e.selection) > 0:
            button.enable()
        else:
            button.disable()


    columns = [{'name': 'name', 'label': 'Name', 'field': 'name', 'required': True, 'align': 'left'}]
    table = ui.table(columns=columns, rows=users,
                     row_key='name',
                     on_select=toggle_delete_button)
    table.set_selection('multiple')


@ui.page("/")
async def index(user_repo: UserRepository = Depends(get_user_repository)):
    async def create() -> None:
        try:
            await user_repo.create(name=name.value)
            ui.notify(f"User: '{name.value}' created successfully", type='positive')
            name.value = ""
            user_list.refresh()
        except IntegrityError:
            ui.notify(f"User: '{name.value}' already exists", type='negative')
            name.value = ""
        except Exception as e:
            ui.notify(f"Error creating user: {str(e)}", type='negative')
            name.value = ""

    with ui.column().classes('mx-auto'):
        # tailwind
        with ui.row().classes('w-full items-center px-4'):
            name = ui.input(label='Name')
            ui.button(on_click=create, icon='add')
        await user_list(user_repo)

