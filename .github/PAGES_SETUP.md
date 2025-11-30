# GitHub Pages Deployment

This repository uses GitHub Actions to automatically build and deploy Sphinx documentation to GitHub Pages.

## Setup

### 1. Enable GitHub Pages

Go to your repository settings:
1. Navigate to **Settings** → **Pages**
2. Under **Source**, select **GitHub Actions**

### 2. Push to Main/Master

The workflow automatically triggers on push to `main` or `master` branch.

## Workflow

The `.github/workflows/docs.yml` workflow:
1. Checks out the code
2. Sets up Python 3.12
3. Installs uv
4. Creates a venv and installs dependencies
5. Builds Sphinx documentation
6. Deploys to GitHub Pages

## Accessing Documentation

After the first successful deployment, your docs will be available at:

```
https://jopdorp.github.io/build123-timber/
```

## Manual Trigger

You can also manually trigger the workflow:
1. Go to **Actions** tab
2. Select "Build and Deploy Documentation"
3. Click **Run workflow**

## Local Preview

To preview locally before pushing:

```bash
source .venv/bin/activate
cd docs
make html
open _build/html/index.html
```

## Troubleshooting

- **Workflow fails**: Check the Actions tab for error logs
- **404 on GitHub Pages**: Ensure GitHub Pages is enabled and set to GitHub Actions source
- **Old version showing**: Wait a few minutes for cache to clear, or hard refresh (Ctrl+Shift+R)
