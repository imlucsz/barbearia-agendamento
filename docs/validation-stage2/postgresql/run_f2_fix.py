"""Create/validate/remove only this run's disposable PostgreSQL; never log secrets."""
import contextlib
import hashlib
import io
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import traceback
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / 'backend'
BASE_OUT = Path(__file__).resolve().parent
OUT = Path(os.environ.get('STAGE2_PG_OUTPUT', str(BASE_OUT / 'runs' / uuid.uuid4().hex)))
assert OUT.resolve().is_relative_to(BASE_OUT.resolve())
OUT.mkdir(parents=True, exist_ok=True)
GROUPS = {'f2': ['test_f2_login_resilience.F2LoginResilienceTests.test_finish_storage_failure_does_not_leave_an_unusable_session', 'test_f2_login_resilience.F2LoginResilienceTests.test_claim_exception_does_not_commit_a_refresh_session', 'test_f2_transaction_consistency.F2TransactionTests', 'test_login_outcomes.LoginOutcomeTests', 'test_auth_stage2_reproductions.Stage2Reproductions', 'test_auth_security_regressions.AuthenticationSecurityTests.test_legacy_login_cannot_overwrite_completed_reset', 'test_auth_security_regressions.AuthenticationSecurityTests.test_argon_login_cannot_issue_session_after_completed_reset', 'test_auth_stage2_concurrency.Stage2ConcurrencyTests', 'test_password_capacity.LoginCapacityLifecycleTests', 'test_f2_postgresql.F2PostgreSQLTests.test_simultaneous_rotation_rechecks_after_real_user_lock_wait', 'test_f2_postgresql.F2PostgreSQLTests.test_login_connection_loss_before_commit_rolls_back_session_and_claim']}


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def preserved_files():
    files = set((ROOT / 'docs' / 'validation-stage2').rglob('*'))
    files.update((BACKEND / 'tests').glob('max_*.py'))
    files.update((BACKEND / 'tests').glob('test_max_*.py'))
    files.add(ROOT / 'frontend/tests/max-security-surface.test.mjs')
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p.is_file() and OUT not in p.parents and BASE_OUT / 'runs' not in p.parents}


def run_worker(group):
    sys.path[:0] = [str(BACKEND), str(BACKEND / 'tests')]
    os.chdir(BACKEND)
    original_stdout = sys.stdout
    captured = io.StringIO()
    records = []

    class Result(unittest.TestResult):
        def startTest(self, test):
            super().startTest(test)
            self.started = time.monotonic()
            self.current = {'test': test.id(), 'status': 'passed'}

        def addSkip(self, test, reason):
            super().addSkip(test, reason)
            self.current.update(status='skipped', reason=reason)

        def problem(self, test, error, status):
            exc = error[1]
            frames = traceback.extract_tb(error[2])
            self.current.update(status=status, exception=type(exc).__name__,
                sqlstate=getattr(getattr(exc, 'orig', exc), 'sqlstate', None),
                frames=[{'file': str(Path(f.filename)), 'line': f.lineno, 'function': f.name}
                        for f in frames])
            # Never persist exception strings, query parameters, cookies, or tokens.
            if test.id().endswith('test_finish_storage_failure_does_not_leave_an_unusable_session'):
                import support
                from app.models.user import LoginAttempt, RefreshToken
                with support.main.SessionLocal() as db:
                    self.current['known_F2_state'] = {'refresh_rows': db.query(RefreshToken).count(),
                        'outcomes': [r.resultado for r in db.query(LoginAttempt).all()]}

        def addError(self, test, error):
            super().addError(test, error)
            self.problem(test, error, 'error')

        def addFailure(self, test, error):
            super().addFailure(test, error)
            self.problem(test, error, 'failed')

        def stopTest(self, test):
            self.current['seconds'] = round(time.monotonic() - self.started, 3)
            records.append(self.current)
            print(self.current['status'] + ' ' + test.id(), file=original_stdout, flush=True)
            super().stopTest(test)

    started = time.monotonic()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        suite = unittest.defaultTestLoader.loadTestsFromNames(GROUPS[group])
        result = Result()
        suite.run(result)
        import support
        from test_f2_postgresql import EVIDENCE
        with support.main.engine.connect() as c:
            from sqlalchemy import text
            idle = None if support.main.engine.dialect.name != 'postgresql' else c.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                                  "AND state='idle in transaction' AND pid<>pg_backend_pid()" )).scalar_one()
        report = {'group': group, 'backend': support.main.engine.dialect.name, 'records': records,
                  'tests_run': result.testsRun, 'passed': sum(r['status'] == 'passed' for r in records),
                  'failed': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
                  'seconds': round(time.monotonic() - started, 3), 'evidence': EVIDENCE,
                  'idle_transactions_at_end': idle,
                  'suppressed_log_sha256': hashlib.sha256(captured.getvalue().encode()).hexdigest()}
        save(group + '.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('records', 'evidence')}), flush=True)
    return result.wasSuccessful()


def orchestrate():
    assert Path(git('rev-parse', '--show-toplevel')).resolve() == ROOT.resolve()
    assert set(git('diff', '--name-only').splitlines()) <= {'backend/app/core/login_rate_limit.py', 'backend/app/routers/auth.py', 'README.md', 'docs/REQUISITOS_STATUS.md'}, 'Unexpected tracked modifications'
    before = preserved_files()
    save('preservation-before.json', before)
    run_id = uuid.uuid4().hex[:12]
    name = 'stage2-pg-validation-' + run_id
    database = 'stage2_' + run_id + '_test'
    username = 'stage2_' + run_id
    password = secrets.token_urlsafe(32)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    environment = dict(os.environ, POSTGRES_USER=username, POSTGRES_DB=database,
                       POSTGRES_PASSWORD=password, POSTGRES_INITDB_ARGS='--encoding=UTF8')
    created = False
    summary = {'commit': git('rev-parse', 'HEAD'), 'container': name, 'label': run_id,
               'port_binding': '127.0.0.1:' + str(port), 'database': database,
               'limits': {'cpus': 1, 'memory_MiB': 512, 'pids': 128, 'tmpfs_MiB': 256},
               'no_persistent_volume': True, 'groups': {}}

    def docker(*args, timeout=35, check=True):
        process = subprocess.run(['docker', *args], env=environment, capture_output=True,
                                 text=True, timeout=timeout, check=False)
        if check and process.returncode:
            raise RuntimeError('Docker command failed: ' + args[0] + '; details suppressed')
        return process

    try:
        creation = docker('run', '-d', '--pull=never', '--name', name,
            '--label', 'stage2.validation.owner=' + run_id,
            '--cpus=1', '--memory=512m', '--pids-limit=128', '--shm-size=64m',
            '--tmpfs', '/var/lib/postgresql/data:rw,nosuid,noexec,size=256m',
            '-p', '127.0.0.1:' + str(port) + ':5432',
            '-e', 'POSTGRES_USER', '-e', 'POSTGRES_DB', '-e', 'POSTGRES_PASSWORD', '-e', 'POSTGRES_INITDB_ARGS',
            'postgres:16-alpine', 'postgres', '-c', 'max_connections=30',
            '-c', 'shared_buffers=64MB', '-c', 'max_wal_size=128MB',
            '-c', 'lock_timeout=5s', '-c', 'statement_timeout=15s',
            '-c', 'idle_in_transaction_session_timeout=30s', '-c', 'deadlock_timeout=100ms')
        created = True
        summary['container_id'] = creation.stdout.strip()
        summary['image_id'] = docker('inspect', '--format', '{{.Image}}', name).stdout.strip()
        save('environment.json', summary)
        ready = False
        for _ in range(30):
            result = docker('exec', name, 'pg_isready', '-U', username, '-d', database, check=False)
            if result.returncode == 0:
                ready = True
                break
            time.sleep(1)
        if not ready:
            raise RuntimeError('Disposable PostgreSQL readiness timed out')
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine import URL
        url = URL.create('postgresql+psycopg', username=username, password=password,
                         host='127.0.0.1', port=port, database=database)
        engine = create_engine(url, hide_parameters=True)
        with engine.connect() as c:
            db, user = c.execute(text('SELECT current_database(), current_user')).one()
            assert db == database and user == username and db.endswith('_test')
            summary['postgresql'] = dict(c.execute(text(
                "SELECT version() AS version,current_setting('server_version_num') AS server_version_num,"
                "current_setting('server_encoding') AS encoding,"
                "(SELECT datcollate FROM pg_database WHERE datname=current_database()) AS collation,"
                "current_setting('transaction_isolation') AS isolation,current_setting('fsync') AS fsync,"
                "current_setting('synchronous_commit') AS synchronous_commit,"
                "current_setting('lock_timeout') AS lock_timeout,current_setting('statement_timeout') AS statement_timeout,"
                "current_setting('deadlock_timeout') AS deadlock_timeout")).mappings().one())
        engine.dispose()
        save('environment.json', summary)
        print('Disposable PostgreSQL ready; identity verified', flush=True)
        env = dict(os.environ, BOOKING_TEST_BACKEND='postgresql',
                   BOOKING_TEST_POSTGRES_URL=url.render_as_string(hide_password=False),
                   PYTHON_DOTENV_DISABLED='1', PYTHONDONTWRITEBYTECODE='1', STAGE2_PG_OUTPUT=str(OUT))
        selected_groups = ['f2']
        for group in selected_groups:
            print('Starting group: ' + group, flush=True)
            started = time.monotonic()
            process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--worker', group],
                                       env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                stdout, stderr = process.communicate(timeout=210)
                # Worker writes only test IDs/counts to stdout. Raw stderr is never exposed.
                print(stdout.strip(), flush=True)
                summary['groups'][group] = {'exit_code': process.returncode,
                    'seconds': round(time.monotonic()-started, 3),
                    'stderr_sha256': hashlib.sha256(stderr.encode()).hexdigest()}
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=10)
                summary['groups'][group] = {'timeout_seconds': 210}
            save('environment.json', summary)
        # The harness should drop every test schema after each worker exits.
        engine = create_engine(url, hide_parameters=True)
        with engine.connect() as c:
            summary['remaining_test_schemas'] = c.execute(text(
                "SELECT nspname FROM pg_namespace WHERE nspname LIKE 'barbearia_test_%' ORDER BY nspname")).scalars().all()
            summary['deadlocks_total'] = c.execute(text(
                'SELECT deadlocks FROM pg_stat_database WHERE datname=current_database()')).scalar_one()
        engine.dispose()
    except Exception as error:  # noqa: BLE001 - sanitize failures and always clean up owned resources
        summary['orchestration_error'] = type(error).__name__
        summary['orchestration_sqlstate'] = getattr(getattr(error, 'orig', error), 'sqlstate', None)
        if not summary['groups']:
            diagnostic = getattr(getattr(error, 'orig', error), 'diag', None)
            summary['preflight_message'] = getattr(diagnostic, 'message_primary', None)
        summary['orchestration_frames'] = [{'function': f.name, 'line': f.lineno}
                                            for f in traceback.extract_tb(error.__traceback__)]
        print('Orchestration failed: ' + type(error).__name__ + '; no credentials logged', flush=True)
    finally:
        save('environment.json', summary)
        if created:
            owner = docker('inspect', '--format', '{{ index .Config.Labels "stage2.validation.owner" }}', name).stdout.strip()
            assert owner == run_id, 'Refuse cleanup of unowned resource'
            removed = docker('rm', '-f', '-v', name)
            summary['cleanup'] = {'owned_container_removed': removed.returncode == 0,
                                  'tmpfs_destroyed': removed.returncode == 0}
        after = preserved_files()
        summary['prior_evidence_preserved'] = before == after
        summary['tracked_diff_after'] = git('diff', '--name-only')
        save('environment.json', summary)
        print(json.dumps({'cleanup': summary.get('cleanup'),
                          'prior_evidence_preserved': summary['prior_evidence_preserved'],
                          'tracked_diff_after': summary['tracked_diff_after']}), flush=True)
    return not summary.get('orchestration_error') and all(
        r.get('exit_code') == 0 for r in summary['groups'].values())


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        raise SystemExit(0 if run_worker(sys.argv[2]) else 1)
    else:
        raise SystemExit(0 if orchestrate() else 1)
