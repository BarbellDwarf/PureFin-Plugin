
using System;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using Jellyfin.Plugin.ContentFilter.Services;
using MediaBrowser.Controller.Session;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.ContentFilter;

/// <summary>
/// Hosted service for Content Filter plugin initialization.
/// </summary>
public class PluginEntryPoint : IHostedService, IDisposable
{
    private readonly ILogger<PluginEntryPoint> _logger;
    private readonly ILoggerFactory _loggerFactory;
    private readonly ISessionManager _sessionManager;
    private PlaybackMonitor? _playbackMonitor;


    /// <summary>
    /// Initializes a new instance of the <see cref="PluginEntryPoint"/> class.
    /// </summary>
    /// <param name="loggerFactory">The logger factory.</param>
    /// <param name="sessionManager">The session manager.</param>
    public PluginEntryPoint(
        ILoggerFactory loggerFactory,
        ISessionManager sessionManager)
    {
        _loggerFactory = loggerFactory;
        _sessionManager = sessionManager;
        _logger = loggerFactory.CreateLogger<PluginEntryPoint>();
    }


    /// <summary>
    /// Starts the Content Filter plugin service.
    /// </summary>
    /// <param name="cancellationToken">A cancellation token.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public async Task StartAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Content Filter plugin starting up");
        
        try
        {
            var plugin = Plugin.Instance;
            if (plugin == null)
            {
                _logger.LogError("Plugin instance is null");
                return;
            }

            // Initialize SegmentStore
            var segmentStore = new SegmentStore(_loggerFactory.CreateLogger<SegmentStore>());
            await segmentStore.LoadAll();
            
            // Initialize PlaybackMonitor
            _playbackMonitor = new PlaybackMonitor(
                _sessionManager,
                segmentStore,
                _loggerFactory.CreateLogger<PlaybackMonitor>());
            
            // Store references in plugin instance using reflection
            var segmentStoreField = typeof(Plugin).GetField("_segmentStore", BindingFlags.NonPublic | BindingFlags.Instance);
            segmentStoreField?.SetValue(plugin, segmentStore);
            
            _logger.LogInformation("Content Filter plugin started successfully - SegmentStore and PlaybackMonitor initialized");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error starting Content Filter plugin");
        }
    }


    /// <summary>
    /// Stops the Content Filter plugin service.
    /// </summary>
    /// <param name="cancellationToken">A cancellation token.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public Task StopAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("Content Filter plugin stopping");
        
        try
        {
            _playbackMonitor?.Dispose();
            _logger.LogInformation("PlaybackMonitor disposed");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error disposing PlaybackMonitor");
        }
        
        return Task.CompletedTask;
    }

    /// <summary>
    /// Disposes resources used by the Content Filter plugin service.
    /// </summary>
    public void Dispose()
    {
        // Cleanup if needed
    }
}
