# Frequently Asked Questions (FAQ)

## General Questions

### What is PureFin Content Filter?

PureFin Content Filter is a Jellyfin plugin that automatically detects and filters objectionable content including nudity, immodesty, violence, and profanity using AI-powered analysis and community-curated data.

### How does it work?

The plugin uses AI services to analyze your media library and create timestamped segments for content that should be filtered. During playback, the plugin monitors the current position and automatically skips or mutes filtered segments.

### Is my data sent to external services?

No. All AI analysis runs on your own server using Docker containers. No data is sent to external services unless you explicitly enable community data integration.

### Does it work with all Jellyfin clients?

The plugin works with most Jellyfin clients that support server-side playback control. Some actions (like skip) work universally, while others (like mute) may have limited client support.

## Installation & Setup

### What are the system requirements?

- Jellyfin 10.8.0+
- Docker Engine 24+
- 8GB+ RAM (16GB recommended)
- 100GB+ free disk space
- Optional: NVIDIA GPU for faster analysis

### Do I need a GPU?

No, a GPU is optional but recommended for faster content analysis. The system works fine with CPU-only processing, though analysis will be slower.

### How long does initial analysis take?

Analysis time depends on your library size and system resources:
- ~2-5 minutes per hour of video on GPU
- ~5-15 minutes per hour of video on CPU

### Can I analyze only specific libraries?

Not yet, but this feature is planned. Currently, the scheduled task analyzes all video libraries.

## Usage Questions

### Can I adjust filtering sensitivity?

Yes, you can choose from three sensitivity levels:
- **Strict**: Very sensitive, filters more content
- **Moderate**: Balanced filtering (default)
- **Permissive**: Less sensitive, filters less content

### Can I manually edit segments?

Currently, manual segment editing is limited. You can disable filtering for specific media items through the metadata editor. Advanced manual editing is planned for a future release.

### How do I disable filtering for a specific movie?

1. Navigate to the movie in Jellyfin
2. Click "Edit Metadata"
3. Find the Content Filter section
4. Disable filtering or adjust settings
5. Save changes

### Can different users have different filtering?

Yes! Each Jellyfin user can have their own filtering preferences with different sensitivity levels and enabled categories.

### What happens during filtered content?

Depending on the action configured:
- **Skip**: Video jumps over the filtered segment
- **Mute**: Audio is muted during the segment (for profanity)

## Technical Questions

### Where is segment data stored?

Segment data is stored as JSON files in the configured segment directory (default: `/segments`). Each media item has its own JSON file.

### How much disk space does it use?

Segment files are very small (typically 1-10KB per media item). A library of 1000 movies would use less than 10MB for segment data.

### Can I backup my segment data?

Yes! Simply backup the segment directory. You can also export segment data through the plugin interface (planned feature).

### Does it slow down playback?

No. The filtering system is designed to have minimal impact on playback. The plugin only monitors playback position and applies actions when needed.

### Can I use my own AI models?

Yes, but this requires modifying the AI services. The services are designed to be modular and you can replace models by updating the Docker containers.

## Troubleshooting

### Plugin doesn't appear in Jellyfin

1. Check that the DLL is in the correct plugins directory
2. Restart Jellyfin completely
3. Check Jellyfin logs for errors
4. Ensure .NET 8.0 is installed

### AI services won't start

1. Check Docker is running: `docker ps`
2. Check service logs: `docker compose logs`
3. Ensure ports 3001-3003 are not in use
4. Verify Docker Compose version 2.0+

### Content is not being filtered

1. Verify analysis has completed for the media item
2. Check segment files exist in segment directory
3. Ensure filtering is enabled in plugin configuration
4. Check user-specific filtering settings
5. Review plugin logs for errors

### Analysis is very slow

1. Enable GPU acceleration in docker-compose.yml
2. Reduce scene detection threshold (analyzes fewer scenes)
3. Adjust sample count per scene
4. Consider upgrading server hardware

### False positives/negatives

1. Adjust sensitivity level in plugin configuration
2. Report issues to help improve AI models
3. Manually review and correct segments
4. Enable community data preference

## Community & Support

### Where can I get help?

- Check this FAQ and documentation
- Search [GitHub Issues](https://github.com/BarbellDwarf/PureFin-Plugin/issues)
- Join community discussions
- Report bugs on GitHub

### How can I contribute?

- Report bugs and suggest features
- Contribute code via pull requests
- Help improve documentation
- Share anonymized segment data for model training

### Is there a roadmap?

Yes! Check the project repository for the development roadmap and planned features.

## Privacy & Security

### What data does the plugin collect?

The plugin only processes media files on your server. No data is collected or sent externally unless you explicitly enable community data features.

### Is it safe to use?

Yes. The plugin runs entirely on your server and uses standard Jellyfin APIs. All AI processing is done locally in Docker containers.

### Can I contribute segment data anonymously?

This feature is planned. When implemented, you'll be able to opt-in to share anonymized segment timestamps to help improve community data.

## Compatibility

### Which Jellyfin versions are supported?

Jellyfin 10.8.0 and higher are officially supported.

### Does it work with Emby or Plex?

No, this plugin is specifically designed for Jellyfin and uses Jellyfin-specific APIs.

### Which video formats are supported?

All video formats supported by FFmpeg, including:
- MP4, MKV, AVI
- MOV, WMV, FLV
- And many more

### Does it work with live TV?

Not currently. The plugin is designed for on-demand media playback.
