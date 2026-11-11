"""SQLite persistence and realistic, clearly labeled demo fixtures."""
from __future__ import annotations
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('RESOLVEIQ_DB', str(ROOT / 'data' / 'resolveiq.db')))


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA busy_timeout=15000')
    return connection


def init_db() -> None:
    with connect() as conn:
        conn.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS issues (
                id TEXT PRIMARY KEY, title TEXT NOT NULL,
                description TEXT NOT NULL,
                reporter TEXT NOT NULL DEFAULT 'Anonymous',
                category TEXT NOT NULL DEFAULT 'General',
                priority TEXT NOT NULL DEFAULT 'Medium',
                status TEXT NOT NULL DEFAULT 'Needs review',
                team TEXT NOT NULL DEFAULT 'Unassigned',
                confidence REAL NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'Offline rules',
                analysis TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                demo INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id TEXT NOT NULL REFERENCES issues(id),
                kind TEXT NOT NULL,
                message TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS activities_issue ON activities(issue_id);
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id TEXT NOT NULL REFERENCES issues(id),
                title TEXT NOT NULL,
                owner TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS playbooks (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                steps TEXT NOT NULL
            );
        ''')
        if not conn.execute('SELECT 1 FROM playbooks LIMIT 1').fetchone():
            playbooks = [
                ('PB-01','Access','Account access recovery','Verify identity, inspect authentication traces, and restore access without exposing credentials.', ['Confirm the affected user and reproduction steps','Check authentication and reset events','Apply approved access recovery and verify sign-in']),
                ('PB-02','Billing','Payment discrepancy review','Cross-check transaction and reconciliation status before any billing changes.', ['Match customer transaction identifiers with ledger entries','Investigate duplicates, gateway status, and settlement','Prepare correction with finance approval']),
                ('PB-03','Technical','Service reliability response','Determine blast radius and collect reproducible evidence before mitigation.', ['Reproduce or verify service symptoms','Review logs, deployment history, and affected services','Implement tested mitigation and monitor recovery']),
                ('PB-04','Security','Security incident containment','Escalate securely; preserve evidence; request explicit approval before sensitive changes.', ['Record indicators and isolate exposed scope','Notify the security incident owner','Prepare containment and recovery checklist']),
                ('PB-05','Operations','Service request fulfillment','Validate requester needs and track delivery through confirmation.', ['Confirm requirement and business impact','Assign accountable service owner','Complete and verify the requested service']),
                ('PB-06','General','Investigation and response','Gather facts, identify owner, and confirm resolution with the reporter.', ['Clarify expected and actual behavior','Identify responsible team and action','Verify outcome and update requester']),
            ]
            conn.executemany('INSERT INTO playbooks VALUES(?,?,?,?,?)',[(i,c,t,s,json.dumps(steps)) for i,c,t,s,steps in playbooks])
        if conn.execute('SELECT COUNT(*) FROM issues').fetchone()[0]:
            return
        examples = [
          ('RI-1042','Students stuck in portal sign-in loop','Several students are redirected back to the login page after entering correct credentials. This started after the latest portal update.','Student services','Access','High','Needs review','Support Operations',.89,5),
          ('RI-1041','Duplicate invoice after successful payment','A customer paid once but two invoices appear in their account. Please verify the charge and correct the duplicate invoice.','Finance desk','Billing','Medium','In progress','Finance Operations',.94,10),
          ('RI-1040','Application upload freezes at 98%','Application documents consistently freeze at 98% in Chrome and Safari, preventing submission for some users.','Admissions team','Technical','High','Needs review','Platform Engineering',.91,17),
          ('RI-1039','Password reset link not arriving','Some users are not receiving their password reset emails even after several attempts.','Help desk','Access','Medium','In progress','Support Operations',.88,26),
          ('RI-1038','Staff dashboard unavailable','The internal dashboard became unavailable for staff during morning operations. Several teams were affected.','Operations lead','Technical','Critical','Resolved','Platform Engineering',.97,46),
          ('RI-1037','Attachment missing on reopened request','A previously submitted attachment disappears from the ticket after the request is reopened.','Quality assurance','Technical','Low','Needs review','Product Engineering',.78,51),
          ('RI-1036','Delayed confirmation notifications','New submissions sometimes take over an hour to send confirmation emails to users.','Student services','Operations','Medium','Resolved','Support Operations',.87,78),
          ('RI-1035','Refund request pending reconciliation','An approved refund has not appeared in the customer account after the agreed window.','Finance desk','Billing','Medium','Needs review','Finance Operations',.84,102),
        ]
        for id_,title,desc,reporter,category,priority,status,team,confidence,hours in examples:
            stamp = (datetime.now(timezone.utc)-timedelta(hours=hours)).replace(microsecond=0).isoformat()
            analysis = {
              'summary': f'{category} request requiring {team.lower()} review.',
              'rationale': 'Demo scenario: seeded for product walkthrough.',
              'suspected_cause': 'Not yet confirmed; investigate before making changes.',
              'recommended_actions': ['Verify the reported behavior','Collect supporting evidence','Confirm resolution with the requester'],
              'draft_reply':'Thanks for reporting this. Our team is reviewing the issue and will update you after verification.',
              'similar_issues': [], 'playbooks': [], 'steps': [
                  {'name':'Triage','result':f'Classified as {priority.lower()} priority · {category}'},
                  {'name':'Knowledge lookup','result':'Matched internal response procedures'},
                  {'name':'Resolution plan','result':'Prepared an actionable review checklist'},
                  {'name':'Team routing','result':f'Proposed {team}'},
                  {'name':'Approval gate','result':'Reviewed by a human' if status!='Needs review' else 'Awaiting human approval'},
              ],
            }
            conn.execute('''INSERT INTO issues(id,title,description,reporter,category,priority,status,team,confidence,source,analysis,created_at,updated_at,demo)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)''',
                 (id_,title,desc,reporter,category,priority,status,team,confidence,'Seeded demo',json.dumps(analysis),stamp,stamp))
            conn.execute('INSERT INTO activities(issue_id,kind,message,detail,created_at) VALUES(?,?,?,?,?)',
                         (id_,'intake','Demo case added','Sample data for evaluation',stamp))
            if status!='Needs review':
                conn.execute('INSERT INTO activities(issue_id,kind,message,detail,created_at) VALUES(?,?,?,?,?)',
                             (id_,'approval','Plan approved and assigned',team,stamp))
            if status=='Resolved':
                conn.execute('INSERT INTO activities(issue_id,kind,message,detail,created_at) VALUES(?,?,?,?,?)',
                             (id_,'resolved','Issue marked resolved','Demo resolution',stamp))


def next_issue_id(conn: sqlite3.Connection) -> str:
    maximum = conn.execute("SELECT COALESCE(MAX(CAST(SUBSTR(id,4) AS INTEGER)),1042) FROM issues").fetchone()[0]
    return f'RI-{maximum+1}'


def issue_dict(row: sqlite3.Row) -> dict:
    val = dict(row)
    val['analysis'] = json.loads(val['analysis'] or '{}')
    val['demo'] = bool(val['demo'])
    return val
