"""ResolveIQ — responsible, human-approved issue-resolution workflow demo."""
from __future__ import annotations
import json
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from db import connect, init_db, next_issue_id, issue_dict, now
from agent import run_workflow, model_config

ROOT=Path(__file__).resolve().parent

@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    yield

app=FastAPI(title='ResolveIQ API',version='1.2.0',lifespan=lifespan)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

class IssueCreate(BaseModel):
    title: str = Field(min_length=5,max_length=180)
    description: str = Field(min_length=15,max_length=4000)
    reporter: str = Field(default='Demo user',max_length=100)

class Decision(BaseModel):
    note: str=Field(default='',max_length=600)

class IssueUpdate(BaseModel):
    status: str
    note: str=Field(default='',max_length=600)


def require(conn,issue_id):
    row=conn.execute('SELECT * FROM issues WHERE id=?',(issue_id,)).fetchone()
    if not row: raise HTTPException(status_code=404,detail='Issue not found')
    return row

@app.get('/')
def index():
    return FileResponse(ROOT/'static'/'index.html')

@app.get('/api/health')
def health():
    return {'ok':True,'engine':model_config(),'version':'1.2.0'}

@app.get('/api/engine')
def engine_status():
    return model_config(force=True)

@app.get('/api/issues')
def list_issues(search: str='',priority:str='',status:str='',limit:int=Query(100,ge=1,le=500)):
    sql='SELECT * FROM issues WHERE 1=1'
    params=[]
    if search.strip():
        sql+=' AND (id LIKE ? OR title LIKE ? OR description LIKE ? OR reporter LIKE ?)'
        params += [f'%{search.strip()}%']*4
    if priority and priority!='All priorities':
        sql+=' AND priority=?'
        params.append(priority)
    if status and status!='All statuses':
        sql+=' AND status=?'
        params.append(status)
    sql+=' ORDER BY CASE priority WHEN \'Critical\' THEN 0 WHEN \'High\' THEN 1 WHEN \'Medium\' THEN 2 ELSE 3 END, created_at DESC LIMIT ?'
    params.append(limit)
    with connect() as conn:
        rows=conn.execute(sql,params).fetchall()
    return [issue_dict(r) for r in rows]

@app.get('/api/issues/{issue_id}')
def get_issue(issue_id:str):
    with connect() as conn:
        row=require(conn,issue_id)
        data=issue_dict(row)
        data['activities']=[dict(x) for x in conn.execute('SELECT * FROM activities WHERE issue_id=? ORDER BY id DESC LIMIT 40',(issue_id,)).fetchall()]
        data['tasks']=[dict(x) for x in conn.execute('SELECT * FROM tasks WHERE issue_id=? ORDER BY id',(issue_id,)).fetchall()]
    return data

@app.post('/api/issues',status_code=201)
def create_issue(payload:IssueCreate):
    with connect() as conn:
        issue_id=next_issue_id(conn)
        stamp=now()
        conn.execute('INSERT INTO issues(id,title,description,reporter,created_at,updated_at) VALUES(?,?,?,?,?,?)',
                     (issue_id,payload.title.strip(),payload.description.strip(),payload.reporter.strip() or 'Demo user',stamp,stamp))
        conn.execute('INSERT INTO activities(issue_id,kind,message,detail,created_at) VALUES(?,?,?,?,?)',
                     (issue_id,'intake','Issue submitted','Agent workflow initiated',stamp))
    try:
        return run_workflow(issue_id)
    except Exception as exc:
        # Keep the submitted issue accessible even if analysis fails.
        with connect() as conn:
            conn.execute('INSERT INTO activities(issue_id,kind,message,detail,created_at) VALUES(?,?,?,?,?)',
                         (issue_id,'error','Automatic analysis unavailable',type(exc).__name__,now()))
        return get_issue(issue_id)

@app.post('/api/issues/{issue_id}/reanalyze')
def reanalyze(issue_id:str):
    with connect() as conn:
        row=require(conn,issue_id)
        if row['status'] not in ('Needs review','Rejected'):
            raise HTTPException(409,'Only pending or rejected issues can be reanalyzed')
    return run_workflow(issue_id)

@app.post('/api/issues/{issue_id}/approve')
def approve(issue_id:str,decision:Decision):
    stamp=now()
    with connect() as conn:
        row=require(conn,issue_id)
        if row['status']!='Needs review':
            raise HTTPException(409,'Issue is not awaiting approval')
        analysis=json.loads(row['analysis'] or '{}')
        actions=analysis.get('recommended_actions') or []
        if not actions:
            raise HTTPException(409,'No plan available for approval')
        for action in actions[:5]:
            if not isinstance(action,str):continue
            conn.execute('INSERT INTO tasks(issue_id,title,owner,status,created_at) VALUES(?,?,?,?,?)',
                         (issue_id,action,row['team'],'Open',stamp))
        conn.execute("UPDATE issues SET status='In progress',updated_at=? WHERE id=?",(stamp,issue_id))
        conn.execute('INSERT INTO activities(issue_id,kind,message,detail,created_at) VALUES(?,?,?,?,?)',
                     (issue_id,'approval','Human approved proposed plan',decision.note or f'Assigned to {row["team"]}',stamp))
        conn.execute('INSERT INTO activities(issue_id,kind,message,detail,created_at) VALUES(?,?,?,?,?)',
                     (issue_id,'action','Internal follow-up tasks created',f'{len(actions[:5])} tasks assigned to {row["team"]}',stamp))
    return get_issue(issue_id)

@app.post('/api/issues/{issue_id}/reject')
def reject(issue_id:str,decision:Decision):
    stamp=now()
    with connect() as conn:
        row=require(conn,issue_id)
        if row['status']!='Needs review': raise HTTPException(409,'Issue is not awaiting review')
        conn.execute("UPDATE issues SET status='Rejected',updated_at=? WHERE id=?",(stamp,issue_id))
        conn.execute('INSERT INTO activities(issue_id,kind,message,detail,created_at) VALUES(?,?,?,?,?)',
                     (issue_id,'rejection','Proposed plan rejected',decision.note or 'Manual review required',stamp))
    return get_issue(issue_id)

@app.patch('/api/issues/{issue_id}')
def update(issue_id:str,payload:IssueUpdate):
    allowed={'Resolved','In progress','Needs review'}
    if payload.status not in allowed: raise HTTPException(400,'Unsupported status')
    stamp=now()
    with connect() as conn:
        row=require(conn,issue_id)
        if payload.status=='Resolved' and row['status']!='In progress':
            raise HTTPException(409,'Approve the plan before resolving an issue')
        if payload.status=='In progress' and row['status']!='In progress':
            raise HTTPException(409,'Approve the plan to begin work')
        conn.execute('UPDATE issues SET status=?,updated_at=? WHERE id=?',(payload.status,stamp,issue_id))
        conn.execute('INSERT INTO activities(issue_id,kind,message,detail,created_at) VALUES(?,?,?,?,?)',
                     (issue_id,'resolved' if payload.status=='Resolved' else 'update',f'Status updated to {payload.status}',payload.note,stamp))
    return get_issue(issue_id)

@app.patch('/api/tasks/{task_id}')
def complete_task(task_id:int):
    with connect() as conn:
        row=conn.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
        if not row:raise HTTPException(404,'Task not found')
        new_status='Done' if row['status']=='Open' else 'Open'
        conn.execute('UPDATE tasks SET status=? WHERE id=?',(new_status,task_id))
        conn.execute('INSERT INTO activities(issue_id,kind,message,detail,created_at) VALUES(?,?,?,?,?)',
                     (row['issue_id'],'task',f'Task marked {new_status.lower()}',row['title'],now()))
        return {'ok':True,'status':new_status}

@app.get('/api/playbooks')
def get_playbooks():
    with connect() as conn:
        return [{**dict(row),'steps':json.loads(row['steps'])} for row in conn.execute('SELECT * FROM playbooks ORDER BY id')]

@app.get('/api/activity')
def recent_activity(limit:int=Query(30,ge=1,le=100)):
    with connect() as conn:
        return [dict(row) for row in conn.execute('''SELECT a.*,i.title AS issue_title,i.priority FROM activities a
                  JOIN issues i ON i.id=a.issue_id ORDER BY a.id DESC LIMIT ?''',(limit,))]

@app.get('/api/dashboard')
def dashboard():
    with connect() as conn:
        total=conn.execute('SELECT COUNT(*) FROM issues').fetchone()[0]
        rows=conn.execute('SELECT status,COUNT(*) AS amount FROM issues GROUP BY status').fetchall()
        status={row['status']:row['amount'] for row in rows}
        priority=[dict(x) for x in conn.execute('SELECT priority,COUNT(*) AS count FROM issues GROUP BY priority').fetchall()]
        today=conn.execute("SELECT COUNT(*) FROM issues WHERE date(created_at)=date('now')").fetchone()[0]
        tasks=conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Open'").fetchone()[0]
        recent=conn.execute('''SELECT * FROM issues ORDER BY datetime(created_at) DESC LIMIT 7''').fetchall()
    return {'total':total,'needs_review':status.get('Needs review',0),'in_progress':status.get('In progress',0),
            'resolved':status.get('Resolved',0),'rejected':status.get('Rejected',0),
            'today':today,'open_tasks':tasks,'priority':priority,'recent':[issue_dict(x) for x in recent],
            'engine':model_config()}
