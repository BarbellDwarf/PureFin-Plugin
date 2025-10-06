using MediaBrowser.Model.Plugins;

namespace Jellyfin.Plugin.ContentFilter.Configuration;

/// <summary>
/// Plugin configuration.
/// </summary>
public class PluginConfiguration : BasePluginConfiguration
{
    /// <summary>
    /// Gets or sets a value indicating whether nudity filtering is enabled.
    /// </summary>
    public bool EnableNudity { get; set; } = true;

    /// <summary>
    /// Gets or sets a value indicating whether immodesty filtering is enabled.
    /// </summary>
    public bool EnableImmodesty { get; set; } = true;

    /// <summary>
    /// Gets or sets a value indicating whether violence filtering is enabled.
    /// </summary>
    public bool EnableViolence { get; set; } = true;

    /// <summary>
    /// Gets or sets a value indicating whether profanity filtering is enabled.
    /// </summary>
    public bool EnableProfanity { get; set; } = true;

    /// <summary>
    /// Gets or sets the sensitivity level (strict, moderate, permissive).
    /// </summary>
    public string Sensitivity { get; set; } = "moderate";

    /// <summary>
    /// Gets or sets the segment directory path.
    /// </summary>
    public string SegmentDirectory { get; set; } = "/segments";

    /// <summary>
    /// Gets or sets a value indicating whether to prefer community data over AI data.
    /// </summary>
    public bool PreferCommunityData { get; set; } = true;

    /// <summary>
    /// Gets or sets the AI service base URL.
    /// </summary>
    public string AiServiceBaseUrl { get; set; } = "http://localhost:3000";

    /// <summary>
    /// Gets or sets a value indicating whether to enable OSD feedback during filtering.
    /// </summary>
    public bool EnableOsdFeedback { get; set; } = false;
}
