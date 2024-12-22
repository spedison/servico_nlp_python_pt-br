from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import socket
import datetime
from nltk.tokenize import PunktTokenizer
from utils.baixa_arquivos import verifica_e_baixa_arquivos
import re
from utils.nlp import lemmatize_sentence, stem_sentence

# Recursos necessários do NLTK
verifica_e_baixa_arquivos("tokenizers", "punkt.zip")
verifica_e_baixa_arquivos("tokenizers", "punkt_tab.zip")
verifica_e_baixa_arquivos("stemmers", "rslp.zip")

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Simulando usuários e tokens
FAKE_USERS_DB = {
    "user1": {"username": "user1", "password": "secret", "token": "token1"},
    "user2": {"username": "user2", "password": "secret", "token": "token2"},
}

def verify_token(token: str = Depends(oauth2_scheme)):
    for user in FAKE_USERS_DB.values():
        if user["token"] == token:
            return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou não fornecido",
        headers={"WWW-Authenticate": "Bearer"},
    )

class Sentence(BaseModel):
    text: str

# Função auxiliar genérica para processar texto
def process_text(sentence: str, processor_function, envia_copia: bool, process_name: str):
    if is_not_palavras(sentence):
        return {"estado": f"Texto inválido para processamento: {process_name}"}
    
    processed_text = processor_function(sentence)
    if envia_copia:
        return {"original": sentence, process_name: processed_text, "estado": "ok"}
    else:
        return {process_name: processed_text, "estado": "ok"}

# Função auxiliar para verificar se o texto contém palavras comuns
def is_not_palavras(text):
    palavras = re.split(r'[\s\t\n.]+', text)
    total_numeros = sum(c.isdigit() for c in text)
    total_letras = sum(c.isalpha() for c in text)
    total_letras_com_numeros = total_numeros + total_letras

    if total_letras_com_numeros == 0:
        return True  # Não há palavras

    palavras_longas = [palavra for palavra in palavras if len(palavra) > 60]
    palavras_curtas = [palavra for palavra in palavras if len(palavra) <= 2]

    if len(palavras) == 0:
        return False  # Evita divisão por zero

    porcentagem_longa = (len(palavras_longas) / len(palavras)) * 100
    porcentagem_curta = (len(palavras_curtas) / len(palavras)) * 100
    porcentagem_numeros = (total_numeros / total_letras_com_numeros) * 100

    return (porcentagem_longa > 80 or porcentagem_curta > 80 or porcentagem_numeros > 80)

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = FAKE_USERS_DB.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": user["token"], "token_type": "bearer"}

@app.get("/")
def read_root(user: dict = Depends(verify_token)):
    return {
        "message": "Hello, World!",
        "date_time": datetime.datetime.utcnow().__str__(),
        "hostname": socket.gethostname(),
        "user": user["username"]
    }

@app.post("/token/copia={envia_copia}")
def token(sentence: Sentence, envia_copia: bool, user: dict = Depends(verify_token)):
    def tokenize_text(text):
        stok = PunktTokenizer("portuguese")
        return stok.tokenize(text)
    return process_text(sentence.text, tokenize_text, envia_copia, "tokens")

@app.post("/lematize/copia={envia_copia}")
def lemmatize(sentence: Sentence, envia_copia: bool, user: dict = Depends(verify_token)):
    return process_text(sentence.text, lemmatize_sentence, envia_copia, "lematizado")

@app.post("/radical/copia={envia_copia}")
def stem(sentence: Sentence, envia_copia: bool, user: dict = Depends(verify_token)):
    return process_text(sentence.text, stem_sentence, envia_copia, "radical")
