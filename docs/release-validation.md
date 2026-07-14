# MES V2 Release Validation

## Purpose

`deploy/windows/Test-MesRelease.ps1` is the local release quality gate. It validates one staged Git revision before server preparation or deployment. It does not publish WPF, copy application files, run Alembic upgrades, change PostgreSQL settings, register tasks, or restart services.

The gate runs these steps in order and continues after a failed step so the final report contains every problem found:

1. Tracked-file, high-confidence secret-pattern, Git state, and WPF Production-setting policy.
2. Complete backend pytest suite.
3. `alembic current --check-heads`.
4. `alembic check` against the local validation database.
5. NuGet restore for the WPF solution.
6. Release build of both `Mes.Wpf` and `Mes.Vendor.Wpf`.
7. Release DLL existence and Production-setting copy/hash verification.
8. Git state comparison proving that validation did not change tracked source.

## Normal Development Run

Run while developing to find all failures. Existing worktree changes produce a warning but do not hide other results.

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File .\deploy\windows\Test-MesRelease.ps1 `
  -RepositoryRoot C:\path\to\mes-v1 `
  -ReportRoot C:\mes_release_validation
```

## Final Release Run

After committing the exact release revision, require a clean worktree:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File .\deploy\windows\Test-MesRelease.ps1 `
  -RepositoryRoot C:\path\to\mes-v1 `
  -ReportRoot E:\MES\release-validation `
  -RequireCleanWorktree
```

Do not place the report root under the Git repository. The script rejects overlapping paths.

Exit codes:

- `0`: every required release check passed.
- `1`: one or more warnings; review before release.
- `2`: at least one critical failure; do not release.

`-SkipDotnetRestore` is available only for a controlled offline rerun with an already restored dependency graph. It always creates a warning and is not acceptable for the final release record.

## Source Policy

The source validator rejects tracked `.env`, private-key, and certificate-bundle files. It scans tracked text for high-confidence private-key, AWS, GitHub, OpenAI, and PostgreSQL credential-URL patterns without writing matched values to the report. PostgreSQL URLs in backend test fixtures are excluded from only that URL rule; private-key and token rules still apply to tests.

Both WPF `appsettings.Production.json` files must contain an absolute, non-loopback API URL with no credentials, query, or fragment. The vendor URL must use HTTPS. Timeout values must be positive and ordered for the internal WPF client. Sensitive key names such as password, secret, token, or database URL are rejected from WPF settings.

This local pattern check is a release guard, not a replacement for protected secret storage, repository access controls, or a remote secret-scanning service after the private repository is enabled.

## Reports

Each run creates a timestamped directory containing:

- `release-validation.json`: overall status, branch, commit, options, and every step result.
- `source-policy.json`: structured tracked-source and Production-setting results.
- `wpf-output.json`: structured Release-output results.
- One text log per command step.

Python bytecode writing is disabled during the gate. Generated .NET outputs remain under ignored `bin` and `obj` paths. The final worktree-integrity step compares Git status before and after validation and fails if the gate itself changed tracked source.

Keep the final successful JSON report with the release record, commit ID, deployment backup ID, migration revision, operator, and deployment result.
