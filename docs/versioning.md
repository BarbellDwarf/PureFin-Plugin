# PureFin Plugin Versioning Policy

## Plugin Version Format

Plugin versions follow `MAJOR.MINOR.PATCH.0` format (the `.0` suffix is required by the Jellyfin plugin system).

| Component | Meaning |
|-----------|---------|
| MAJOR | Breaking change to plugin behavior or configuration schema |
| MINOR | New feature or significant change |
| PATCH | Bug fix or minor improvement |
| .0 | Always 0 (Jellyfin format requirement) |

**Current version:** 1.0.1.0

## ABI Versioning

The `targetAbi` in `build.yaml` specifies the minimum Jellyfin server version required.

| targetAbi | Minimum Jellyfin Version |
|-----------|--------------------------|
| 10.11.0.0 | Jellyfin 10.11.x and newer |

**Current targetAbi:** 10.11.0.0

This means the plugin is compatible with Jellyfin 10.11.x.

## Model Versioning

AI models are versioned independently of the plugin using semantic versioning (`MAJOR.MINOR.PATCH`).

| Model | Current Version | Schema Version |
|-------|-----------------|----------------|
| nsfw-mobilenet | 1.0.0 | 1.0 |
| violence-classifier | 1.0.0 | 1.0 |

**Schema version** governs the output format of model inference responses. The plugin requires a minimum schema version. If a model's schema version is incompatible, the plugin will refuse to use it and log an error.

## Release Channels

| Channel | Tag Pattern | Description |
|---------|-------------|-------------|
| Stable | `v1.0.0.0` | Production-ready releases |
| Pre-release | `v1.0.0.0-beta.1` | Testing/early access |
| Nightly | `nightly-YYYYMMDD` | Automated builds (not in manifest) |

## AI Services Versioning

AI services use independent semantic versions and tags from the plugin:

| Component | Tag Pattern | Version Format |
|-----------|-------------|----------------|
| Jellyfin plugin | `v1.2.3.0` | `MAJOR.MINOR.PATCH.0` |
| AI services stack | `ai-services-v1.2.3` | `MAJOR.MINOR.PATCH` |

On pushes to `main`, the AI services workflow computes the next `ai-services-v*` version and only publishes artifacts for services whose files were affected (or all services if shared stack files changed).

## Release Process

1. Update `build.yaml` version field
2. Update `CHANGELOG.md`
3. Create and push a version tag: `git tag v1.0.1.0 && git push origin v1.0.1.0`
4. GitHub Actions automatically:
   - Builds and packages the plugin
   - Creates a GitHub Release with zip + checksums
   - Updates `repository.json` on `gh-pages` branch

## Adding to Jellyfin

Users can add the plugin repository in Jellyfin:
1. Go to **Dashboard → Plugins → Repositories**
2. Click **+** and add: `https://BarbellDwarf.github.io/PureFin-Plugin/repository.json`
3. Go to **Dashboard → Plugins → Catalog** and search for PureFin
4. Install and restart Jellyfin
