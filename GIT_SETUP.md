# GitHub setup for the empty Team 9 repository

The supplied GitHub repository is currently empty. This package intentionally does **not** contain a pre-made Git history or fake author identities. That keeps the final contribution history attributable to the actual students.

## First integration commit (Karan)

After cloning the empty repository, copy the contents of this package into it, then run:

```bash
git add .
git commit -m "chore: initialize Sprint 1 EIMS baseline"
git push -u origin main
```

Use Karan's real GitHub identity/email. Do not use the placeholder email from any example.

## Team branches

After the baseline is on `main`, each member should create their own branch from the latest `main`:

```bash
git fetch origin
git checkout main
git pull origin main
```

Karan:
```bash
git checkout -b feature/karan-api-coordination
```

Krishitha:
```bash
git checkout -b feature/krishitha-inventory-api
```

Jayashree:
```bash
git checkout -b test/jayashree-api-tests
```

Hemavathi:
```bash
git checkout -b qa/hemavathi-ci-security
```

Each person must set their own Git identity once:

```bash
git config user.name "Your Full Name"
git config user.email "your-github-email@example.com"
```

Then make only their assigned changes, run tests, and push their branch:

```bash
git add <files>
git commit -m "type(scope): concise change"
git push -u origin <branch-name>
```

Open a pull request into `main`. Do not directly push feature branches into `main` unless the team has explicitly chosen that workflow.

## Review rule

Before merging:

```bash
pytest -q
```

The GitHub Actions workflow must also be green. Keep commits small and logically grouped. Do not rewrite or force-push `main`.
