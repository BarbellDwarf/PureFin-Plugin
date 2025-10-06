using System;
using System.Threading.Tasks;
using Jellyfin.Plugin.ContentFilter.Services;
using MediaBrowser.Controller.Plugins;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.ContentFilter;

/// <summary>
/// Plugin entry point for initialization.
/// </summary>
public class PluginEntryPoint : IServerEntryPoint
{
    private readonly ILogger<PluginEntryPoint> _logger;
    private readonly SegmentStore _segmentStore;

    /// <summary>
    /// Initializes a new instance of the <see cref="PluginEntryPoint"/> class.
    /// </summary>
    /// <param name="segmentStore">Segment store.</param>
    /// <param name="logger">Logger.</param>
    public PluginEntryPoint(
        SegmentStore segmentStore,
        ILogger<PluginEntryPoint> logger)
    {
        _segmentStore = segmentStore;
        _logger = logger;
    }

    /// <inheritdoc />
    public Task RunAsync()
    {
        _logger.LogInformation("Content Filter plugin starting up");
        
        // Load all segments from disk
        _ = _segmentStore.LoadAll();
        
        _logger.LogInformation("Content Filter plugin started successfully");
        
        return Task.CompletedTask;
    }

    /// <inheritdoc />
    public void Dispose()
    {
        // Cleanup if needed
    }
}
