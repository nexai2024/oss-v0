from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Assuming main.py creates a 'templates' instance
# from ..main import templates # This can cause circular import if main also imports this.
# A better way is to have templates initialized in a config module or passed around.
# For this structure, let's assume templates is accessible or re-initialized here if simple.
# However, the prompt implies main.py's `templates` instance should be used.
# This requires careful structuring or passing `templates` object.
# For now, to make it runnable as a module, let's re-initialize.
# In a refactor, dependency injection or a shared config for `templates` would be better.

templates = Jinja2Templates(directory="backend/app/templates")
# This assumes the working directory allows this relative path.
# When run with uvicorn from root, "backend/app/templates" is correct.

router = APIRouter(
    prefix="/view", # Prefix for all routes in this router
    tags=["Frontend Pages"],
    default_response_class=HTMLResponse # Default for these routes
)

@router.get("/")
async def read_root_ui():
    # Redirects /view/ to /view/login
    return RedirectResponse(url="/view/login", status_code=302)

@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.get("/dashboard")
async def dashboard_page(request: Request):
    # The actual auth check is client-side in JS (checks localStorage)
    # Server-side protection for direct access would require more (e.g., cookies or server session)
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/prompts")
async def prompts_list_page(request: Request):
    return templates.TemplateResponse("prompts_list.html", {"request": request})

@router.get("/prompts/new")
async def prompt_create_page(request: Request):
    return templates.TemplateResponse("prompt_form.html", {"request": request, "mode": "create"})

@router.get("/prompts/{prompt_id}/edit")
async def prompt_edit_page(request: Request, prompt_id: int): # prompt_id captured for context if needed by template
    return templates.TemplateResponse("prompt_form.html", {"request": request, "prompt_id": prompt_id, "mode": "edit"})

@router.get("/prompts/{prompt_id}")
async def prompt_detail_page(request: Request, prompt_id: int): # prompt_id captured for context
    return templates.TemplateResponse("prompt_detail.html", {"request": request, "prompt_id": prompt_id})

# API Endpoint Pages
@router.get("/endpoints")
async def api_endpoints_list_page(request: Request):
    return templates.TemplateResponse("api_endpoints_list.html", {"request": request})

@router.get("/endpoints/new")
async def api_endpoint_create_page(request: Request):
    return templates.TemplateResponse("api_endpoint_form.html", {"request": request, "mode": "create"})

@router.get("/endpoints/{endpoint_id}/edit")
async def api_endpoint_edit_page(request: Request, endpoint_id: int):
    return templates.TemplateResponse("api_endpoint_form.html", {"request": request, "endpoint_id": endpoint_id, "mode": "edit"})

# Skipping dedicated detail page for API endpoints for now.

@router.get("/api-access-keys")
async def api_access_keys_page(request: Request):
    return templates.TemplateResponse("api_access_keys.html", {"request": request})

@router.get("/logs")
async def api_call_logs_page(request: Request): # endpoint_id can be passed as query param
    return templates.TemplateResponse("api_call_logs.html", {"request": request})

# A root redirect for the whole app, if desired, would be in main.py
# For example, GET "/" redirects to "/view/login"
# This router only handles routes under its own prefix "/view"
