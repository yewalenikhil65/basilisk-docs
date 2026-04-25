# Build Policy

Documentation builds run on GitHub Actions with limited free minutes (2,000/month).

## Rules

- **Pushes to `main` do NOT trigger builds.** Commit freely without worrying about billing.
- **Automatic builds**: Weekly on Monday 6am UTC (~4 builds/month, ~12 minutes total).
- **Manual builds**: Trigger from the [Actions tab](../../actions) → "Build and Deploy Basilisk Docs" → "Run workflow" when you need an immediate update.

## Why

Each build takes ~2-3 minutes. Limiting to ~4 builds/month uses <1% of the free allowance, leaving room for other repos.

## To trigger a build manually

1. Go to [Actions](../../actions)
2. Click "Build and Deploy Basilisk Docs"
3. Click "Run workflow" → "Run workflow"
