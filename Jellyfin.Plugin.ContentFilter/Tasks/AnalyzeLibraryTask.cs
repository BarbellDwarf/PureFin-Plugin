using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
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
    public string Name => "Analyze Library for Content Filter";

    /// <inheritdoc />
    public string Key => "ContentFilterAnalyzeLibrary";

    /// <inheritdoc />
    public string Description => "Analyzes media library for objectionable content";

    /// <inheritdoc />
    public string Category => "Content Filter";

    /// <inheritdoc />
    public async Task ExecuteAsync(IProgress<double> progress, CancellationToken cancellationToken)
    {
        _logger.LogInformation("Starting library analysis for content filter");

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
    }

    /// <inheritdoc />
    public IEnumerable<TaskTriggerInfo> GetDefaultTriggers()
    {
        return new[]
        {
            new TaskTriggerInfo
            {
                Type = TaskTriggerInfo.TriggerDaily,
                TimeOfDayTicks = TimeSpan.FromHours(3).Ticks
            }
        };
    }

    private async Task AnalyzeItem(BaseItem item, CancellationToken cancellationToken)
    {
        // Check if item already has segments
        var existingSegments = _segmentStore.Get(item.Id.ToString());
        if (existingSegments != null)
        {
            _logger.LogDebug("Item {Name} already analyzed, skipping", item.Name);
            return;
        }

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

        // Store segments
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

    private Task<List<Segment>> AnalyzeVideo(string videoPath, CancellationToken cancellationToken)
    {
        var config = Plugin.Instance?.Configuration;
        if (config == null)
        {
            return Task.FromResult(new List<Segment>());
        }

        try
        {
            // In production, this would make actual HTTP calls to AI services
            // For now, return mock data
            var segments = new List<Segment>();

            // Mock segment generation based on enabled categories
            if (config.EnableNudity)
            {
                segments.Add(new Segment
                {
                    Start = 120.0,
                    End = 135.0,
                    Categories = new[] { "nudity" },
                    Action = "skip",
                    Confidence = 0.85,
                    Source = "ai"
                });
            }

            return Task.FromResult(segments);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error analyzing video: {Path}", videoPath);
            return Task.FromResult(new List<Segment>());
        }
    }
}
