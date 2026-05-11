# Analytics Pipeline Branch Guide

This document outlines the recommended Git workflow for the analytics pipeline features.

## Creating a Feature Branch

```bash
# Start from main
git checkout main
git pull origin main

# Create and switch to feature branch
git checkout -b feature/analytics-pipeline
```

## Branch Organization

### Option 1: Single Feature Branch (Recommended for this scope)
```bash
git checkout -b feature/analytics-pipeline
# Implement:
# - Google Sheets auto-reporter
# - PySpark ML pipeline
# - GitHub Actions workflow
git push origin feature/analytics-pipeline
# Create Pull Request on GitHub
```

### Option 2: Separate Feature Branches (For larger teams)
```bash
# Branch 1: Sheets automation
git checkout -b feature/google-sheets-reporter
# → automation/google_sheets_reporter.py
# → .github/workflows/weekly_report.yml

# Branch 2: PySpark pipeline
git checkout -b feature/pyspark-ml-pipeline
# → ml/pyspark_pipeline.py

# Both can be PRed separately or merged together
```

## Commits to Include

```bash
git add automation/google_sheets_reporter.py
git commit -m "feat: add Google Sheets auto-reporter with weekly schedule"

git add .github/workflows/weekly_report.yml
git commit -m "ci: add GitHub Actions workflow for weekly reports"

git add ml/pyspark_pipeline.py
git commit -m "feat: implement PySpark ML pipeline with temporal splits"

git add requirements.txt
git commit -m "build: add dependencies for Sheets API and PySpark"

git add ANALYTICS_PIPELINE.md
git commit -m "docs: add analytics pipeline setup and usage guide"

git add .gitignore
git commit -m "build: update .gitignore for sensitive files and outputs"
```

## Pull Request Template

```markdown
## Description
Implemented analytics pipeline: Google Sheets auto-reporter + PySpark ML pipeline

## What's Changed
- ✅ Google Sheets API integration with weekly schedule
- ✅ GitHub Actions workflow for automated reporting
- ✅ PySpark ML pipeline (temporal splits, rolling features)
- ✅ Synthetic data generation for testing
- ✅ Setup documentation and troubleshooting guide

## Setup Instructions
1. Create Google Cloud project and service account
2. Share Google Sheet with service account email
3. Add `GOOGLE_SERVICE_ACCOUNT_KEY` and `SPREADSHEET_ID` secrets to GitHub
4. Run locally: `python automation/google_sheets_reporter.py`
5. Run PySpark: `python ml/pyspark_pipeline.py`

## Testing
- [x] Local test with synthetic data
- [x] Sheets API authentication
- [ ] Manual trigger of GitHub Actions workflow (after merge)
- [ ] Weekly schedule verification (after 1 week)

## Related Issues
Closes #XX (if applicable)
```

## Branch Protection Rules (Optional but Recommended)

To prevent accidental commits to main:

1. Go to repo → **Settings → Branches**
2. Add rule for `main`:
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require code reviews before merging (1+ reviewers)
   - ✅ Dismiss stale pull request approvals

## Merge and Clean Up

```bash
# After PR is approved and merged:
git checkout main
git pull origin main

# Delete local branch
git branch -d feature/analytics-pipeline

# Delete remote branch
git push origin --delete feature/analytics-pipeline
```

## Viewing All Branches

```bash
# Local branches
git branch

# Remote branches
git branch -r

# All branches with last commit info
git branch -a --format='%(refname:short) - %(committerdate:short) - %(subject)'
```

---

**Tip**: Use `git log --oneline` to see commit history on your branch before pushing.
