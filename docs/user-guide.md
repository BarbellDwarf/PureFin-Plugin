# User Guide

## Overview

Content Filter provides automatic detection and filtering of objectionable content in your Jellyfin media library, including:
- Nudity
- Immodesty (revealing clothing)
- Violence
- Profanity

## How It Works

1. **Analysis**: AI services analyze your media library to detect objectionable content
2. **Segmentation**: Content is divided into time-based segments with category labels
3. **Filtering**: During playback, the plugin automatically skips or mutes flagged segments

## Getting Started

### Initial Setup

1. Install and configure the plugin (see [Installation Guide](./install.md))
2. Run the initial library analysis
3. Configure your filtering preferences
4. Start watching filtered content!

### Configuring Filters

Navigate to **Dashboard** → **Plugins** → **Content Filter**

**Enable/Disable Categories**: Toggle filtering for specific content types
**Sensitivity Level**: Choose strict, moderate, or permissive filtering
**User Preferences**: Set different preferences for each Jellyfin user

### Using Filtered Content

Filtered content plays automatically with objectionable segments skipped or muted:

- **Skip Action**: Video jumps over the filtered segment
- **Mute Action**: Audio is muted during the segment (for profanity)

### Manual Overrides

Override automatic filtering for specific media:

1. Navigate to media item
2. Click **Edit Metadata**
3. Adjust Content Filter settings
4. Save changes

### Reviewing Segments

View detected segments for a media item:

1. Open media details
2. Navigate to Content Filter section
3. Review flagged segments with timestamps
4. Edit or remove incorrect segments

## Best Practices

### Sensitivity Selection

- **Strict**: Best for young children, filters more content
- **Moderate**: Balanced for general family viewing
- **Permissive**: Minimal filtering for adult viewers

### Regular Analysis

Schedule automatic library analysis:
- Run analysis after adding new content
- Re-analyze periodically for improved accuracy
- Configure scheduled tasks in Jellyfin dashboard

### Feedback and Improvement

Help improve filtering accuracy:
- Report false positives/negatives
- Manually correct segments
- Share anonymized data for model training (optional)

## Advanced Features

### Per-User Profiles

Create custom filtering profiles for different users:
- Children: Strict filtering, all categories enabled
- Teenagers: Moderate filtering, selective categories
- Adults: Permissive or no filtering

### Community Data

Leverage community-curated segment data:
- More accurate than AI-generated data
- Manually reviewed by users
- Automatically merged with AI segments

### Custom Actions

Configure custom actions for filtered content:
- Skip entirely
- Mute audio only
- Blur video (if supported)
- Show warning notification

## Troubleshooting

See [Troubleshooting Guide](./troubleshooting.md) for common issues and solutions.

## FAQ

See [FAQ](./faq.md) for frequently asked questions.
