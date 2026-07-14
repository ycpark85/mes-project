@{
    # This file contains paths and service names only. Never put passwords,
    # database URLs, API keys, or tokens in a deployment config.
    BackendRoot = 'C:\MES\v2\current\backend'
    PythonPath = 'C:\MES\v2\current\backend\.venv\Scripts\python.exe'
    EnvFile = 'C:\MES\config\backend.env'
    MonitorEnvFile = 'C:\MES\config\monitor.env'
    BackupRoot = 'E:\MES\backups'
    MonitorHistoryRoot = 'E:\MES\monitoring\history'
    RestoreRecordPath = 'E:\MES\monitoring\last-restore.json'
    OperationsLogRoot = 'E:\MES\monitoring\logs'
    PgBin = 'C:\Program Files\PostgreSQL\17\bin'
    ApiBaseUrl = 'http://127.0.0.1:8000'
    ApiServiceName = 'MES-API'
    PostgresServiceName = 'postgresql-x64-17'
    TaskPrincipal = 'NT AUTHORITY\SYSTEM'
    BackupTime = '02:00'
    MonitorTime = '03:00'
}
