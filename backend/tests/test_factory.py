import json
import os
import zipfile
import io

os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['FACTORY_TOKEN'] = 'test-token'
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine, SQLModel, Session, select
from fastapi.testclient import TestClient
import pytest
import main
import core

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'engine', create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool))
    monkeypatch.setattr(core, 'ROOT', tmp_path)
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    with TestClient(main.app) as client:
        client.headers['Authorization'] = 'Bearer test-token'
        yield client

@pytest.mark.parametrize('name',['../evil.py','/etc/passwd','x/../../evil','a\\b', '.env', 'a/.git/config', 'C:evil'])
def test_paths(name):
    with pytest.raises(ValueError): core.validate_files({name:'bad'})

def test_syntax():
    assert not core.static_check({'bad.py':'def x(', 'README.md':'ok'})['passed']
    assert core.static_check({'app.py':'x = 1','README.md':'ok'})['passed']

def test_auth(client):
    assert client.get('/api/projects',headers={'Authorization':'wrong'}).status_code == 401

def test_missing_credentials_and_consent(client,monkeypatch):
    monkeypatch.delenv('MODEL_API_KEY',raising=False)
    assert client.post('/api/projects',json={'prompt':'Build a calculator'}).status_code == 400
    assert client.post('/api/projects',json={'prompt':'Build a calculator','approve_model_costs':True}).status_code == 409

def test_export(client):
    p=main.Project(prompt='test',revision=1,status='syntax_passed')
    with Session(main.engine) as session:
        session.add(p);session.commit();session.refresh(p)
    core.save_revision(p.id,1,{'README.md':'real data','app.py':'print(1)'})
    response=client.get('/api/projects/'+p.id+'/zip')
    assert zipfile.ZipFile(io.BytesIO(response.content)).read('app.py') == b'print(1)'
    assert client.post('/api/projects/'+p.id+'/test',json={'approve_execution':True}).status_code==403

def test_repair_loop(client,monkeypatch):
    class TestProvider:
        calls=0
        tokens=0
        async def ask(self,role,prompt,json_output=False):
            self.calls+=1
            if role=='Developer': return {'README.md':'start','app.py':'def broken('}
            if role=='Debugger': return {'README.md':'start','app.py':'print(42)'}
            return 'Test fixture analysis'
    monkeypatch.setattr(main,'Provider',TestProvider)
    p=main.Project(prompt='Build a real application')
    with Session(main.engine) as session:
        session.add(p);session.commit();session.refresh(p)
    import asyncio
    asyncio.run(main.build(p.id))
    result=client.get('/api/projects/'+p.id).json()
    assert result['status']=='syntax_passed'
    assert result['revision']==2
    assert result['files']['app.py']=='print(42)'
    assert (core.ROOT/p.id/'1'/'app.py').read_text()=='def broken('

def test_provider_http_contract(monkeypatch):
    import asyncio
    import httpx
    original= httpx.AsyncClient
    def handler(request):
        assert request.url.path=='/v1/chat/completions'
        assert request.headers['authorization']=='Bearer fixture-key'
        body=json.loads(request.content)
        assert body['response_format']=={'type':'json_object'}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'files':{'README.md':'Run instructions'}})}}],'usage':{'total_tokens':42}})
    monkeypatch.setenv('MODEL_API_KEY','fixture-key')
    monkeypatch.setattr(core.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    provider=core.Provider()
    assert asyncio.run(provider.ask('Developer','Build',True))=={'README.md':'Run instructions'}
    assert provider.tokens==42
