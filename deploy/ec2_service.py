"""Private, preloaded FastAPI model service. No business write tools or AWS credentials."""
import time,threading
from contextlib import asynccontextmanager
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,ConfigDict,StrictFloat,StrictInt,StrictBool
from lab import LocalLLM,predict
from deploy import model_handler as model
_lock=threading.Lock();_startup=None
@asynccontextmanager
async def lifespan(app):
    global _startup
    t=time.perf_counter();model._model=LocalLLM('/var/task/model');_startup=time.perf_counter()-t
    print({'event':'model_ready','startup_seconds':round(_startup,3),'parameters':model._model.parameter_count},flush=True)
    yield
app=FastAPI(title='Private Business Decision Model',lifespan=lifespan,docs_url=None,redoc_url=None)
class Inputs(BaseModel):
    model_config=ConfigDict(extra='forbid')
    TV:StrictInt|StrictFloat
    radio:StrictInt|StrictFloat
    newspaper:StrictInt|StrictFloat
class Request(BaseModel):
    model_config=ConfigDict(extra='forbid')
    inputs:Inputs
    include_context:StrictBool=True
@app.get('/health')
def health():
    return {'status':'ready' if model._model is not None else 'starting','model':'Qwen/Qwen2.5-0.5B-Instruct','parameters':model._model.parameter_count if model._model else None,'startup_model_load_seconds':_startup}
@app.post('/analyze')
def analyze(x:Request):
    values=x.inputs.model_dump()
    try:
        predict(values)
        if any(v>1000 for v in values.values()):raise ValueError()
    except (ValueError,AssertionError):raise HTTPException(422,'Bounded numeric scenario required')
    if not _lock.acquire(blocking=False):raise HTTPException(503,'Model is busy')
    try:
        result=model.handler({'inputs':values,'include_context':x.include_context},None)
        if result['status']!='ok':raise HTTPException(503,'Model unavailable')
        return {**result,'serving':'preloaded container on isolated EC2','startup_model_load_seconds':_startup}
    finally:_lock.release()
