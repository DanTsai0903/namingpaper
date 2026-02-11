---
name: release
description: Guide the release procedure for namingpaper - version bump, commit, GitHub release, and PyPI publish.
metadata:
  author: namingpaper
  version: "1.0"
---

# Release Procedure

Follow these steps to release a new version of namingpaper. The user should provide the version number (X.Y.Z).

## Steps

1. **Bump version** in both `pyproject.toml` and `src/namingpaper/__init__.py`
2. **Commit and push**: `git add -A && git commit -m "Bump version to X.Y.Z" && git push origin main`
3. **Create GitHub release**: `gh release create vX.Y.Z --title "vX.Y.Z" --prerelease --notes "..."`
   - Drop `--prerelease` for stable releases
4. **Build and publish to PyPI**:
   ```bash
   uv build
   source .env  # contains UV_PUBLISH_TOKEN
   uv publish --token "$UV_PUBLISH_TOKEN"
   ```
5. **Clean old dists** if needed: `rm -rf dist/` before building to avoid uploading stale files

## Important

- Always confirm the version number with the user before starting.
- Ask whether this is a stable or prerelease before creating the GitHub release.
