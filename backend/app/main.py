from fastapi import FastAPI
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from .routers import auth, users, prompts, api_endpoints, hosted_apis, frontend_pages # Import frontend_pages

app = FastAPI(title="Prompt Pilot API")

# Mount static files
app.mount("/static", StaticFiles(directory="backend/app/static"), name="static")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="backend/app/templates")

# Include the routers for defined API operations
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(prompts.router)
app.include_router(api_endpoints.router)

# Include the router for dynamically hosted APIs
# This should generally be one of the last routers included if it has very broad path parameters
app.include_router(hosted_apis.router)

# Include frontend pages router
# Prefix is defined within frontend_pages.py router itself as "/view"
app.include_router(frontend_pages.router)


@app.get("/")
async def root_redirect_to_login(request: Request):
    # Redirect the root of the application to the login page
    return RedirectResponse(url="/view/login", status_code=302)
