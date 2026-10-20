import asyncio
import io
import json
import os
import secrets
import uuid
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import Column, Text
from sqlmodel import SQLModel, Session, Field, create_engine, select

from core import Provider, ROOT, save_revision, static_check, sandbox

engine = create_engine(os.getenv('DATABASE_URL', 'sqlite:///./factory.db'), **({'connect_args': {'check_same_thread': False}} if os.getenv('DATABASE_URL', 'sqlite:').startswith('sqlite:') else {}))
tasks = set()
lock = asyncio.Lock()

class Project(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    prompt: str
    status: str = 'queued'
    revision: int = 0
    payload: str = Field(default='{}', sa_column=Column(Text))

class Create(BaseModel):
    prompt: str = Field(min_length=10, max_length=12000)
    approve_model_costs: bool = False

class RunTests(BaseModel):
    approve_execution: bool = False

def read(pid):
    with Session(engine) as session:
        p = session.get(Project, pid)
        if not p:
            raise HTTPException(404, 'Projekt nicht gefunden')
        return p

def update(pid, **values):
    with Session(engine) as session:
        p = session.get(Project, pid)
        for key, value in values.items():
            setattr(p, key, value)
        session.add(p)
        session.commit()

def event(pid, agent, message, **extra):
    p = read(pid)
    data = json.loads(p.payload)
    data.setdefault('events', []).append({'time': datetime.now(timezone.utc).isoformat(), 'agent': agent, 'message': message})
    data.update(extra)
    update(pid, payload=json.dumps(data))

async def build(pid):
    async with lock:
        provider = Provider()
        try:
            update(pid, status='running')
            prompt = read(pid).prompt
            context = prompt
            for role in ['Architect', 'Model Engineer', 'Designer']:
                event(pid, role, 'Modellanalyse läuft')
                result = await provider.ask(role, context)
                event(pid, role, result)
                context += f'\n{role}: {result}'
            event(pid, 'Developer', 'Erzeuge vollständige Projektdateien')
            files = await provider.ask('Developer', context, True)
            for attempt in range(3):
                revision = attempt + 1
                save_revision(pid, revision, files)
                update(pid, revision=revision)
                report = static_check(files)
                event(pid, 'Tester', 'Statische Prüfung abgeschlossen', report=report)
                if report['passed']:
                    break
                if attempt < 2:
                    event(pid, 'Debugger', 'Korrigiere gemeldete Syntaxfehler')
                    files = await provider.ask('Debugger', json.dumps({'requirements': prompt, 'files': files, 'report': report}), True)
            event(pid, 'Optimizer', 'Prüfe Wartbarkeit und Verbesserungsmöglichkeiten')
            review = await provider.ask('Optimizer', json.dumps({'requirements': prompt, 'files': files}))
            event(pid, 'Optimizer', review)
            update(pid, status='syntax_passed' if report['passed'] else 'needs_fix')
        except Exception as exc:
            event(pid, 'Orchestrator', str(exc) if isinstance(exc, ValueError) else f'Verarbeitung abgebrochen ({type(exc).__name__})')
            update(pid, status='failed')
        finally:
            event(pid, 'Orchestrator', 'Auftrag beendet', usage={'calls': provider.calls, 'tokens': provider.tokens})

@asynccontextmanager
async def lifespan(app):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        for p in session.exec(select(Project).where(Project.status.in_(['queued', 'running', 'testing']))):
            p.status = 'interrupted'
            session.add(p)
        session.commit()
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

def auth(request: Request):
    token = os.getenv('FACTORY_TOKEN', '')
    if not token:
        raise HTTPException(503, 'FACTORY_TOKEN serverseitig konfigurieren')
    given = request.headers.get('Authorization', '').removeprefix('Bearer ')
    if not secrets.compare_digest(given, token):
        raise HTTPException(401, 'Ungültiger Zugangsschlüssel')

app = FastAPI(title='AI FACTORY', lifespan=lifespan, dependencies=[Depends(auth)])

@app.get('/api/settings')
def settings():
    return {'model': os.getenv('MODEL_NAME', 'gpt-4.1-mini'), 'configured': bool(os.getenv('MODEL_API_KEY')), 'max_calls': int(os.getenv('MAX_MODEL_CALLS', '12')), 'execution': os.getenv('ENABLE_SANDBOX') == 'true', 'limitations': ['Kein automatisches Deployment oder Fine-Tuning', 'Containerprüfungen: nur Python-Standardbibliothek/unittest', 'Syntaxprüfung ist kein Funktionsnachweis', 'Kosten hängen vom Anbieter ab; Aufruflimit ist kein Geldlimit']}

@app.get('/api/projects')
def projects():
    with Session(engine) as session:
        return session.exec(select(Project)).all()

@app.post('/api/projects', status_code=202)
async def create(body: Create):
    if not body.approve_model_costs:
        raise HTTPException(400, 'Modellkosten müssen ausdrücklich freigegeben werden')
    if not os.getenv('MODEL_API_KEY'):
        raise HTTPException(409, 'MODEL_API_KEY fehlt')
    if len(tasks) >= 4:
        raise HTTPException(429, 'Warteschlange voll')
    p = Project(prompt=body.prompt)
    with Session(engine) as session:
        session.add(p)
        session.commit()
        session.refresh(p)
    task = asyncio.create_task(build(p.id))
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return p

@app.get('/api/projects/{pid}')
def detail(pid: str):
    p = read(pid)
    return {**p.model_dump(), 'data': json.loads(p.payload), 'files': files_for(p)}

def files_for(p):
    directory = ROOT / p.id / str(p.revision)
    if not p.revision or not directory.exists():
        return {}
    return {str(f.relative_to(directory)): f.read_text() for f in directory.rglob('*') if f.is_file()}

@app.get('/api/projects/{pid}/zip')
def export(pid: str):
    files = files_for(read(pid))
    if not files:
        raise HTTPException(409, 'Noch keine Dateien vorhanden')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return Response(buf.getvalue(), media_type='application/zip', headers={'Content-Disposition': f'attachment; filename="ai-factory-{pid}.zip"'})

@app.post('/api/projects/{pid}/test')
async def test_project(pid: str, body: RunTests):
    if not body.approve_execution or os.getenv('ENABLE_SANDBOX') != 'true':
        raise HTTPException(403, 'Container-Ausführung muss serverseitig aktiviert und ausdrücklich freigegeben sein')
    p = read(pid)
    if p.status not in ['syntax_passed', 'needs_fix', 'tested', 'test_failed']:
        raise HTTPException(409, 'Projekt ist nicht prüfbereit')
    files = files_for(p)
    if not any(n.startswith('tests/') and n.endswith('.py') for n in files):
        raise HTTPException(409, 'Keine Python-Tests unter tests/ vorhanden')
    update(pid, status='testing')
    try:
        report = await sandbox(ROOT / pid / str(p.revision))
        event(pid, 'Tester', 'Containerprüfung abgeschlossen', runtime_report=report)
        update(pid, status='tested' if report['passed'] else 'test_failed')
        return report
    except OSError:
        update(pid, status='test_failed')
        raise HTTPException(503, 'Docker ist nicht verfügbar')
