"""Run: pytest -q (httpx is needed for FastAPI's TestClient)."""
import os
from pathlib import Path
from fastapi.testclient import TestClient

os.environ['RESOLVEIQ_DB']='/tmp/resolveiq_test_case.db'
try:Path(os.environ['RESOLVEIQ_DB']).unlink()
except FileNotFoundError:pass

from app import app


def test_end_to_end():
    with TestClient(app) as c:
        assert c.get('/api/health').json()['ok']
        initial=c.get('/api/dashboard').json()
        assert initial['total']>=8
        result=c.post('/api/issues',json={
            'title':'System down for all users',
            'description':'The entire service is down and all users cannot access the dashboard after the last update.',
            'reporter':'QA test'
        })
        assert result.status_code==201,result.text
        body=result.json()
        assert body['priority']=='Critical'
        assert body['status']=='Needs review'
        assert len(body['analysis']['steps'])==5
        assert body['source'].startswith('Offline rules')
        assert body['team']=='Platform Engineering'
        assert isinstance(body['confidence'],(int,float))
        issue_id=body['id']
        assert c.post(f'/api/issues/{issue_id}/approve',json={'note':'Approved during QA'}).status_code==200
        assert c.post(f'/api/issues/{issue_id}/approve',json={}).status_code==409
        detail=c.get(f'/api/issues/{issue_id}').json()
        assert detail['status']=='In progress'
        assert len(detail['tasks'])>=2
        task=detail['tasks'][0]
        assert c.patch(f'/api/tasks/{task["id"]}').json()['status']=='Done'
        assert c.patch(f'/api/issues/{issue_id}',json={'status':'Resolved','note':'Verified'}).status_code==200
        assert c.get('/api/issues',params={'status':'Resolved'}).status_code==200
        assert c.get('/api/activity').status_code==200
        assert c.get('/api/playbooks').status_code==200
        assert c.post(f'/api/issues/{issue_id}/reject',json={}).status_code==409


def test_rejection_path():
    with TestClient(app) as c:
        created=c.post('/api/issues',json={'title':'Duplicate charge on invoice',
            'description':'There are two payments for one invoice and customer wants correction.',
            'reporter':'Finance'}).json()
        assert created['category']=='Billing'
        r=c.post(f'/api/issues/{created["id"]}/reject',json={'note':'Need more evidence'})
        assert r.status_code==200
        assert r.json()['status']=='Rejected'
        again=c.post(f'/api/issues/{created["id"]}/reanalyze')
        assert again.status_code==200
        assert again.json()['status']=='Needs review'


def test_security_requires_review_and_routes_correctly():
    with TestClient(app) as c:
        result=c.post('/api/issues',json={
            'title':'Possible unauthorized access to admin account',
            'description':'Unusual account activity suggests unauthorized access. Security team must review indicators.',
            'reporter':'Security desk'})
        assert result.status_code==201
        data=result.json()
        assert data['category']=='Security'
        assert data['team']=='Security Operations'
        assert data['priority'] in ('High','Critical')
        assert c.patch(f"/api/issues/{data['id']}",json={'status':'Resolved'}).status_code==409
        assert not c.get(f"/api/issues/{data['id']}").json()['tasks']
