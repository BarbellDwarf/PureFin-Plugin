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
    /// Gets or sets the confidence threshold for nudity detection (0.0 to 1.0).
    /// Higher values = more strict filtering, only high-confidence detections.
    /// </summary>
    public double NudityThreshold { get; set; } = 0.35;

    /// <summary>
    /// Gets or sets the confidence threshold for immodesty detection (0.0 to 1.0).
    /// Higher values = more strict filtering, only high-confidence detections.
    /// </summary>
    public double ImmodestyThreshold { get; set; } = 0.20;

    /// <summary>
    /// Gets or sets the confidence threshold for violence detection (0.0 to 1.0).
    /// Higher values = more strict filtering, only high-confidence detections.
    /// </summary>
    public double ViolenceThreshold { get; set; } = 0.45;

    /// <summary>
    /// Gets or sets the confidence threshold for profanity detection (0.0 to 1.0).
    /// Higher values = more strict filtering, only high-confidence detections.
    /// </summary>
    public double ProfanityThreshold { get; set; } = 0.30;

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
    public string AiServiceBaseUrl { get; set; } = "http://localhost:3002";

    /// <summary>
    /// Gets or sets a value indicating whether to enable OSD feedback during filtering.
    /// </summary>
    public bool EnableOsdFeedback { get; set; } = false;

    /// <summary>
    /// Gets or sets the scene detection method (ffmpeg, sampling, transnetv2).
    /// </summary>
    public string SceneDetectionMethod { get; set; } = "transnetv2";

    /// <summary>
    /// Gets or sets the FFmpeg scene detection threshold (0.0 to 1.0).
    /// Used when SceneDetectionMethod is "ffmpeg".
    /// </summary>
    public double FfmpegSceneThreshold { get; set; } = 0.3;

    /// <summary>
    /// Gets or sets the sampling interval in seconds.
    /// Used when SceneDetectionMethod is "sampling".
    /// </summary>
    public int SamplingIntervalSeconds { get; set; } = 30;
}
