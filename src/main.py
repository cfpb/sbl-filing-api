from fastapi import FastAPI

from routers import filing_router

app = FastAPI()


app.include_router(filing_router, prefix="/v1/filing")
