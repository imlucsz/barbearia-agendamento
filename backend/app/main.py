from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Barbearia Agendamento",
    version="1.0.0"
)

app.add_middlewares(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "Backend da Barbearia operando perfeitamente!"}