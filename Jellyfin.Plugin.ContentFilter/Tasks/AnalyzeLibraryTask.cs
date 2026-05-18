using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using Jellyfin.Plugin.ContentFilter.Configuration;
using Jellyfin.Plugin.ContentFilter.Models;
using Jellyfin.Plugin.ContentFilter.Services;
using MediaBrowser.Controller.Entities;
using MediaBrowser.Controller.Library;
using MediaBrowser.Model.Tasks;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.ContentFilter.Tasks;

/// <summary>
/// Scheduled task to analyze library content.
/// </summary>
public class AnalyzeLibraryTask : IScheduledTask
{
    private readonly ILibraryManager _libraryManager;
    private readonly SegmentStore _segmentStore;
    private readonly ILogger<AnalyzeLibraryTask> _logger;
    private readonly IHttpClientFactory _httpClientFactory;

    /// <summary>
    /// Initializes a new instance of the <see cref="AnalyzeLibraryTask"/> class.
    /// </summary>
    /// <param name="libraryManager">Library manager.</param>
    /// <param name="segmentStore">Segment store.</param>
    /// <param name="logger">Logger.</param>
    /// <param name="httpClientFactory">HTTP client factory.</param>
    public AnalyzeLibraryTask(
        ILibraryManager libraryManager,
        SegmentStore segmentStore,
        ILogger<AnalyzeLibraryTask> logger,
        IHttpClientFactory httpClientFactory)
    {
        _libraryManager = libraryManager;
        _segmentStore = segmentStore;
        _logger = logger;
        _httpClientFactory = httpClientFactory;
    }

    /// <inheritdoc />
    public string Name => "Analyze Library for PureFin";

    /// <inheritdoc />
    public string Key => "ContentFilterAnalyzeLibrary";

    /// <inheritdoc />
    public string Description => "Analyzes media library for objectionable content";

    /// <inheritdoc />
    public string Category => "PureFin";

    /// <inheritdoc />
    public async Task ExecuteAsync(IProgress<double> progress, CancellationToken cancellationToken)
    {
        _logger.LogInformation("Starting library analysis for PureFin");

        // Get all video items
        var query = new InternalItemsQuery
        {
            IncludeItemTypes = new[] { Jellyfin.Data.Enums.BaseItemKind.Movie, Jellyfin.Data.Enums.BaseItemKind.Episode },
            IsVirtualItem = false,
            Recursive = true
        };

        var items = _libraryManager.GetItemList(query);
        _logger.LogInformation("Found {Count} video items to analyze", items.Count);

        var processed = 0;
        foreach (var item in items)
        {
            if (cancellationToken.IsCancellationRequested)
            {
                _logger.LogInformation("Analysis cancelled");
                break;
            }

            try
            {
                await AnalyzeItem(item, cancellationToken);
                processed++;
                progress.Report((double)processed / items.Count * 100);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error analyzing item {Name}", item.Name);
            }
        }

        _logger.LogInformation("Library analysis complete. Processed {Count} items", processed);
        
        // With dynamic filtering, no need to reload segments after analysis
        // The segments contain raw scores and filtering is applied at playback time
        _logger.LogInformation("Library analysis complete - segments contain raw AI scores for dynamic filtering");
    }

    /// <inheritdoc />
    public IEnumerable<TaskTriggerInfo> GetDefaultTriggers()
    {
        return new[]
        {
            new TaskTriggerInfo
            {
                Type = TaskTriggerInfoType.DailyTrigger,
                TimeOfDayTicks = TimeSpan.FromHours(3).Ticks
            }
        };
    }

    private async Task AnalyzeItem(BaseItem item, CancellationToken cancellationToken)
    {
        // Always analyze items to get fresh data with updated thresholds
        // Remove the existing segments check to force re-analysis
        
        // Get video path
        var path = item.Path;
        if (string.IsNullOrEmpty(path))
        {
            _logger.LogWarning("Item {Name} has no path", item.Name);
            return;
        }

        _logger.LogInformation("Analyzing {Name} at {Path}", item.Name, path);

        // Call AI service to analyze video
        var segments = await AnalyzeVideo(path, cancellationToken);

        // Store segments (this will overwrite existing segments)
        var segmentData = new SegmentData
        {
            MediaId = item.Id.ToString(),
            Version = 1,
            Segments = segments,
            CreatedAt = DateTime.UtcNow
        };

        await _segmentStore.Put(item.Id.ToString(), segmentData);
        _logger.LogInformation("Stored {Count} segments for {Name}", segments.Count, item.Name);
    }

    private async Task<List<Segment>> AnalyzeVideo(string videoPath, CancellationToken cancellationToken)
    {
        var config = Plugin.Instance?.Configuration;
        if (config == null)
        {
            _logger.LogWarning("Plugin configuration not available");
            return new List<Segment>();
        }

        try
        {
            // Call scene analyzer AI service
            var sceneAnalyzerUrl = $"{config.AiServiceBaseUrl.TrimEnd('/')}/analyze";
            
            // Convert Jellyfin path to container path
            var containerPath = ConvertToContainerPath(videoPath, config);
            
            _logger.LogInformation("Calling scene analyzer at {Url} for {Path} (container path: {ContainerPath})", 
                sceneAnalyzerUrl, videoPath, containerPath);

            var httpClient = _httpClientFactory.CreateClient();
            httpClient.Timeout = TimeSpan.FromMinutes(30); // Long timeout for video processing

            var requestData = new
            {
                video_path = containerPath,
                threshold = 0.15,  // Lower threshold to detect more scenes
                sample_count = 5,
                scene_detection_method = config.SceneDetectionMethod ?? "transnetv2",
                ffmpeg_scene_threshold = config.FfmpegSceneThreshold,
                sampling_interval = config.SamplingIntervalSeconds
            };

            var jsonString = System.Text.Json.JsonSerializer.Serialize(requestData);
            var requestContent = new StringContent(jsonString, System.Text.Encoding.UTF8, "application/json");
            var response = await httpClient.PostAsync(sceneAnalyzerUrl, requestContent, cancellationToken);

            if (!response.IsSuccessStatusCode)
            {
                var error = await response.Content.ReadAsStringAsync(cancellationToken);
                _logger.LogError("Scene analyzer returned error: {Status} - {Error}", response.StatusCode, error);
                return new List<Segment>();
            }

            var responseData = await response.Content.ReadFromJsonAsync<SceneAnalyzerResponse>(cancellationToken: cancellationToken);
            if (responseData == null || !responseData.Success)
            {
                _logger.LogError("Invalid response from scene analyzer");
                return new List<Segment>();
            }

            _logger.LogInformation("Scene analyzer found {Count} scenes for {Path}", responseData.SceneCount, videoPath);

            // Convert AI service response to plugin segments with raw scores
            var segments = new List<Segment>();
            foreach (var scene in responseData.Scenes)
            {
                // Store ALL raw AI scores - filtering will be applied dynamically at playback time
                var rawScores = new Dictionary<string, double>();
                
                // Always store the raw scores, regardless of thresholds
                if (scene.Analysis.Nudity > 0)
                    rawScores["nudity"] = scene.Analysis.Nudity;
                    
                if (scene.Analysis.Immodesty > 0)
                    rawScores["immodesty"] = scene.Analysis.Immodesty;
                    
                if (scene.Analysis.Violence > 0)
                    rawScores["violence"] = scene.Analysis.Violence;

                // Only create a segment if there are any detected scores above minimum threshold (e.g. 0.05)
                const double minimumDetectionThreshold = 0.05;
                var hasContent = rawScores.Values.Any(score => score > minimumDetectionThreshold);
                
                if (hasContent)
                {
                    segments.Add(new Segment
                    {
                        Start = scene.Start,
                        End = scene.End,
                        RawScores = rawScores, // Store raw AI scores
                        Categories = Array.Empty<string>(), // Will be computed dynamically based on current config
                        Action = "skip", // Default action for detected content
                        Source = "ai"
                    });
                }
            }

            _logger.LogInformation("Generated {Count} segments with raw AI scores - filtering will be applied dynamically based on current UI thresholds", 
                segments.Count);
            return segments;
        }
        catch (System.Net.Http.HttpRequestException ex)
        {
            _logger.LogError(ex, "Error connecting to AI service at {Url}. Make sure the service is running.", config.AiServiceBaseUrl);
            return new List<Segment>();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error analyzing video: {Path}", videoPath);
            return new List<Segment>();
        }
    }

    /// <summary>
    /// Convert a Jellyfin file path to the path accessible by the AI service containers,
    /// using the JellyfinMediaPath → AiServiceMediaPath mapping from plugin configuration.
    /// </summary>
    private static string ConvertToContainerPath(string jellyfinPath, PluginConfiguration config)
    {
        // Config-driven mapping (preferred: set these in the plugin UI)
        if (!string.IsNullOrEmpty(config.JellyfinMediaPath) && !string.IsNullOrEmpty(config.AiServiceMediaPath))
        {
            var jfRoot = config.JellyfinMediaPath.TrimEnd('/', '\\');
            var aiRoot = config.AiServiceMediaPath.TrimEnd('/');

            // Normalise to forward slashes for comparison
            var normalised = jellyfinPath.Replace('\\', '/');
            var normalisedRoot = jfRoot.Replace('\\', '/');

            if (normalised.StartsWith(normalisedRoot, StringComparison.OrdinalIgnoreCase))
            {
                return aiRoot + normalised[normalisedRoot.Length..];
            }
        }

        // Built-in fallbacks for common Docker Desktop on Windows patterns
        var path = jellyfinPath.Replace('\\', '/');

        // D:/Media/Movies/... → /mnt/media/...
        if (path.StartsWith("D:/Media/Movies", StringComparison.OrdinalIgnoreCase))
        {
            return "/mnt/media" + path["D:/Media/Movies".Length..];
        }

        // /data/media/movies/... (Jellyfin Docker default) → /mnt/media/...
        if (path.StartsWith("/data/media/movies", StringComparison.OrdinalIgnoreCase))
        {
            return "/mnt/media" + path["/data/media/movies".Length..];
        }

        // /mnt/Media/ → /mnt/media/  (case normalise)
        if (path.StartsWith("/mnt/Media/", StringComparison.Ordinal))
        {
            return "/mnt/media" + path["/mnt/Media".Length..];
        }

        // /media/ → /mnt/media/
        if (path.StartsWith("/media/", StringComparison.Ordinal))
        {
            return "/mnt/media" + path["/media".Length..];
        }

        return path;
    }

    /// <summary>
    /// Response model for scene analyzer API.
    /// </summary>
    private class SceneAnalyzerResponse
    {
        [JsonPropertyName("success")]
        public bool Success { get; set; }

        [JsonPropertyName("scene_count")]
        public int SceneCount { get; set; }

        [JsonPropertyName("scenes")]
        public List<SceneResult> Scenes { get; set; } = new();
    }

    /// <summary>
    /// Scene result from analyzer.
    /// </summary>
    private class SceneResult
    {
        [JsonPropertyName("start")]
        public double Start { get; set; }

        [JsonPropertyName("end")]
        public double End { get; set; }

        [JsonPropertyName("analysis")]
        public SceneAnalysis Analysis { get; set; } = new();
    }

    /// <summary>
    /// Scene analysis data.
    /// </summary>
    private class SceneAnalysis
    {
        [JsonPropertyName("nudity")]
        public double Nudity { get; set; }

        [JsonPropertyName("immodesty")]
        public double Immodesty { get; set; }

        [JsonPropertyName("violence")]
        public double Violence { get; set; }

        [JsonPropertyName("confidence")]
        public double Confidence { get; set; }
    }
}
