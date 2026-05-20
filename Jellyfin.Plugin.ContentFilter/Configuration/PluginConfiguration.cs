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
    /// Revealing-clothing and partial-skin scenes typically score 0.05–0.40;
    /// lower this threshold to catch more borderline content.
    /// </summary>
    public double ImmodestyThreshold { get; set; } = 0.10;

    /// <summary>
    /// Gets or sets the confidence threshold for violence detection (0.0 to 1.0).
    /// Higher values = more strict filtering, only high-confidence detections.
    /// NOTE: The violence classifier outputs a baseline of ~0.50 for all action/war
    /// movie content. Thresholds below 0.65 will false-positive on virtually every
    /// scene in action films. Set to 0.65+ to catch only truly explicit violence.
    /// </summary>
    public double ViolenceThreshold { get; set; } = 0.65;

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
    /// Gets or sets additional AI service base URLs used for load spreading/failover.
    /// Accepts comma, semicolon, or newline-separated values.
    /// </summary>
    public string AiServiceBaseUrls { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets AI service endpoint selection mode.
    /// Supported values: "round_robin" (default), "failover".
    /// </summary>
    public string AiServiceLoadBalancingMode { get; set; } = "round_robin";

    /// <summary>
    /// Gets or sets a value indicating whether to enable OSD feedback during filtering.
    /// </summary>
    public bool EnableOsdFeedback { get; set; } = false;

    /// <summary>
    /// Gets or sets the Jellyfin media root path as seen by Jellyfin (host or container path).
    /// Used to remap paths when forwarding analysis requests to AI services.
    /// Example: /data/media/movies  (Jellyfin Docker default)
    /// Leave empty to pass paths through unchanged.
    /// </summary>
    public string JellyfinMediaPath { get; set; } = string.Empty;

    /// <summary>
    /// Gets or sets the media root path as seen by the AI service containers.
    /// Example: /mnt/media
    /// Only used when JellyfinMediaPath is also set.
    /// </summary>
    public string AiServiceMediaPath { get; set; } = "/mnt/media";

    /// <summary>
    /// Gets or sets a minimum immodesty score required to confirm a nudity detection.
    /// When greater than 0.0, nudity-only detections (high nudity but near-zero immodesty)
    /// are rejected as false positives. Recommended: 0.05.
    /// Set to 0.0 to disable confirmation and flag on nudity score alone.
    /// </summary>
    public double NudityConfirmationMinImmodesty { get; set; } = 0.05;

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

    /// <summary>
    /// Gets or sets the number of frames sampled per detected scene.
    /// Higher values increase catch-rate for short content but increase analysis time.
    /// </summary>
    public int SceneSampleCount { get; set; } = 9;

    /// <summary>
    /// Returns a copy of this configuration with NSFW and violence thresholds derived from
    /// the <see cref="Sensitivity"/> preset, overriding the individual slider values.
    /// </summary>
    public PluginConfiguration WithSensitivityThresholds()
    {
        var (nudityThreshold, immodestyThreshold, violenceThreshold) = SensitivityThresholds.GetThresholds(Sensitivity);
        return new PluginConfiguration
        {
            EnableNudity = EnableNudity,
            EnableImmodesty = EnableImmodesty,
            EnableViolence = EnableViolence,
            EnableProfanity = EnableProfanity,
            NudityThreshold = nudityThreshold,
            ImmodestyThreshold = immodestyThreshold,
            ViolenceThreshold = violenceThreshold,
            ProfanityThreshold = ProfanityThreshold,
            Sensitivity = Sensitivity,
            SegmentDirectory = SegmentDirectory,
            PreferCommunityData = PreferCommunityData,
            AiServiceBaseUrl = AiServiceBaseUrl,
            AiServiceBaseUrls = AiServiceBaseUrls,
            AiServiceLoadBalancingMode = AiServiceLoadBalancingMode,
            EnableOsdFeedback = EnableOsdFeedback,
            SceneDetectionMethod = SceneDetectionMethod,
            FfmpegSceneThreshold = FfmpegSceneThreshold,
            SamplingIntervalSeconds = SamplingIntervalSeconds,
            SceneSampleCount = SceneSampleCount,
            JellyfinMediaPath = JellyfinMediaPath,
            AiServiceMediaPath = AiServiceMediaPath,
            NudityConfirmationMinImmodesty = NudityConfirmationMinImmodesty
        };
    }
}

/// <summary>
/// Maps the Sensitivity preset string to concrete score thresholds per content category.
/// Lower thresholds = more aggressive filtering (more content is caught).
/// Immodesty uses a lower threshold than nudity because revealing-clothing scenes
/// score in the 0.15–0.40 range on the NSFW model, while explicit nudity scores 0.60+.
/// </summary>
public static class SensitivityThresholds
{
    /// <summary>
    /// Returns (NudityThreshold, ImmodestyThreshold, ViolenceThreshold) for the given sensitivity preset.
    /// <list type="bullet">
    ///   <item><term>strict</term><description>0.30 / 0.10 / 0.65 — catches borderline reveals including background bikinis</description></item>
    ///   <item><term>moderate</term><description>0.50 / 0.25 / 0.70 — balanced (default); requires clear revealing clothing or clear violence</description></item>
    ///   <item><term>permissive</term><description>0.75 / 0.45 / 0.82 — only very-high-confidence content</description></item>
    /// </list>
    /// <para>
    /// Violence thresholds are set high (0.65+) because the <c>framasoft/vit-base-violence-detection</c>
    /// model outputs a noise floor of ~0.49–0.51 for all action/motion content regardless of actual violence.
    /// Truly violent scenes score 0.60–0.80+; thresholds below 0.65 cause false positives on all action films.
    /// </para>
    /// <para>
    /// Immodesty thresholds were raised vs. initial calibration after analysis of a PG-13 action film (2F2F)
    /// showed that the nsfw-detector binary mapping (immodesty = nsfw_score × 0.4) produced scores of
    /// 0.10–0.20 for ordinary background beach elements. moderate=0.25 filters meaningful revealing content
    /// while ignoring ambient beachwear in wide-shots.
    /// </para>
    /// </summary>
    public static (double NudityThreshold, double ImmodestyThreshold, double ViolenceThreshold) GetThresholds(string? sensitivity) =>
        sensitivity?.ToLowerInvariant() switch
        {
            "strict" => (0.30, 0.10, 0.65),
            "permissive" => (0.75, 0.45, 0.82),
            _ => (0.50, 0.25, 0.70) // moderate
        };
}
