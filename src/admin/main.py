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

# Global state for pagination
current_page = 1
current_page_size = 50

@ui.refreshable
async def user_list(user_repo: UserRepository) -> None:
    global current_page, current_page_size
    # Get paginated users
    user_models, total_count = await user_repo.get_paginated(current_page, current_page_size)
    users = [UserSchema.from_db_model(model).model_dump() for model in user_models]
    
    # Calculate pagination info
    total_pages = (total_count + current_page_size - 1) // current_page_size if total_count > 0 else 0
    
    ui.label(f"Users (Page {current_page} of {total_pages}, Total: {total_count})")

    selected = []
    async def delete():
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
            selected.clear()
            button.disable()
            
        except Exception as e:
            ui.notify(f"Error deleting users: {str(e)}", type='negative')
            user_list.refresh()
            selected.clear()
            button.disable()

    button = ui.button(on_click=delete, icon='delete')

    button.disable()
    def toggle_delete_button(e):
        selected.clear()
        selected.extend(e.selection)
        if len(selected) > 0:
            button.enable()
        else:
            button.disable()

    columns = [{'name': 'name', 'label': 'Name', 'field': 'name', 'required': True, 'align': 'left'}]
    table = ui.table(columns=columns, rows=users,
                     row_key='name',
                     on_select=toggle_delete_button)
    table.set_selection('multiple')
    
    # Pagination controls
    with ui.row().classes('w-full justify-center items-center gap-2 mt-4'):
        # Page size selector
        page_size_select = ui.select(
            options=[10, 25, 50, 100], 
            value=current_page_size,
            label='Page Size'
        ).classes('w-24')
        
        # Previous page button
        prev_button = ui.button('Previous', icon='chevron_left')
        if current_page <= 1:
            prev_button.disable()
        
        # Page info
        ui.label(f"Page {current_page} of {total_pages}")
        
        # Next page button
        next_button = ui.button('Next', icon='chevron_right')
        if current_page >= total_pages:
            next_button.disable()
        
        # Page navigation handlers
        async def go_to_previous():
            global current_page
            if current_page > 1:
                current_page -= 1
                user_list.refresh()
        
        async def go_to_next():
            global current_page
            if current_page < total_pages:
                current_page += 1
                user_list.refresh()
        
        async def change_page_size():
            global current_page, current_page_size
            current_page = 1
            current_page_size = page_size_select.value
            user_list.refresh()
        
        prev_button.on_click(go_to_previous)
        next_button.on_click(go_to_next)
        page_size_select.on('update:model-value', change_page_size)


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

