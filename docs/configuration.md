# Configuration Guide

## Plugin Configuration

Access plugin configuration through: **Dashboard** → **Plugins** → **Content Filter**

### Content Categories

Enable or disable filtering for each content category:

- **Nudity**: Detects full or partial nudity in video content
- **Immodesty**: Detects revealing clothing and immodest attire
- **Violence**: Detects violent content including weapons, blood, and fighting
- **Profanity**: Detects profane language in audio tracks

### Sensitivity Levels

Choose the appropriate sensitivity level for your needs:

#### Strict
- **Nudity Threshold**: 0.1 (very sensitive)
- **Immodesty Threshold**: 0.2
- **Violence Threshold**: 0.15
- **Use Case**: Families with young children, strict content requirements

#### Moderate (Default)
- **Nudity Threshold**: 0.3 (balanced)
- **Immodesty Threshold**: 0.5
- **Violence Threshold**: 0.4
- **Use Case**: General family viewing, balanced filtering

#### Permissive
- **Nudity Threshold**: 0.7 (less sensitive)
- **Immodesty Threshold**: 0.8
- **Violence Threshold**: 0.7
- **Use Case**: Adult viewers, minimal filtering

### Directory Settings

**Segment Directory**: Location where content segment data is stored
- Default: `/segments`
- Ensure the directory is writable by Jellyfin
- This directory will contain JSON files with timestamp data for filtered content

### AI Service Settings

**AI Service Base URL**: Base URL for AI content analysis services
- Default: `http://localhost:3000`
- For Docker deployments, use appropriate service URLs
- Ensure services are accessible from Jellyfin server

### Data Source Preferences

**Prefer Community Data**: When enabled, community-curated segment data takes precedence over AI-generated data
- Default: Enabled
- Community data is typically manually reviewed and more accurate
- AI data fills gaps where community data is unavailable

### User Interface

**Enable OSD Feedback**: Show on-screen notifications when content is filtered
- Default: Disabled
- When enabled, displays brief messages like "Content Filtered: Violence"
- May be distracting for some users

## Scheduled Tasks

Configure automatic content analysis:

1. Navigate to **Dashboard** → **Scheduled Tasks**
2. Find "Analyze Library for Content Filter"
3. Set schedule (e.g., daily at 3 AM)
4. Configure trigger conditions

## Backup and Restore

### Backup Configuration

```bash
# Plugin configuration
cp /var/lib/jellyfin/config/plugins/ContentFilter.xml ~/backup/

# Segment data
tar -czf segments_backup.tar.gz /segments/
```

### Restore Configuration

```bash
# Restore plugin configuration
cp ~/backup/ContentFilter.xml /var/lib/jellyfin/config/plugins/

# Restore segment data
tar -xzf segments_backup.tar.gz -C /
```

## See Also

- [Installation Guide](./install.md)
- [User Guide](./user-guide.md)
- [Troubleshooting](./troubleshooting.md)
