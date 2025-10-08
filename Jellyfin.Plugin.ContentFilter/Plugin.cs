using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Jellyfin.Plugin.ContentFilter.Configuration;
using Jellyfin.Plugin.ContentFilter.Services;
using MediaBrowser.Common.Configuration;
using MediaBrowser.Common.Plugins;
using MediaBrowser.Controller.Session;
using MediaBrowser.Model.Plugins;
using MediaBrowser.Model.Serialization;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.ContentFilter;

/// <summary>
/// The main plugin class for Content Filter.
/// </summary>
public class Plugin : BasePlugin<PluginConfiguration>, IHasWebPages
{
    private readonly ILogger<Plugin> _logger;
    private SegmentStore? _segmentStore;
    private PlaybackMonitor? _playbackMonitor;
    private ISessionManager? _sessionManager;

    /// <summary>
    /// Initializes a new instance of the <see cref="Plugin"/> class.
    /// </summary>
    /// <param name="applicationPaths">Instance of the <see cref="IApplicationPaths"/> interface.</param>
    /// <param name="xmlSerializer">Instance of the <see cref="IXmlSerializer"/> interface.</param>
    /// <param name="loggerFactory">Logger factory.</param>
    /// <param name="sessionManager">Optional session manager for playback monitoring.</param>
    public Plugin(
        IApplicationPaths applicationPaths,
        IXmlSerializer xmlSerializer,
        ILoggerFactory loggerFactory,
        ISessionManager? sessionManager = null)
        : base(applicationPaths, xmlSerializer)
    {
        Instance = this;
        _sessionManager = sessionManager;
        _logger = loggerFactory.CreateLogger<Plugin>();
        _logger.LogInformation("Content Filter Plugin initialized");
        
        // Initialize services immediately
        InitializeServices();
    }

    /// <inheritdoc />
    public override string Name => "Content Filter";

    /// <inheritdoc />
    public override Guid Id => Guid.Parse("a3f8c6e0-4b2a-4d3c-8e9f-1a2b3c4d5e6f");

    /// <summary>
    /// Gets the current plugin instance.
    /// </summary>
    public static Plugin? Instance { get; private set; }

    /// <summary>
    /// Gets the segment store instance.
    /// </summary>
    public SegmentStore? SegmentStore
    {
        get
        {
            if (_segmentStore == null)
            {
                InitializeServices();
            }
            return _segmentStore;
        }
    }



    /// <inheritdoc />
    public IEnumerable<PluginPageInfo> GetPages()
    {
        return new[]
        {
            new PluginPageInfo
            {
                Name = this.Name,
                EmbeddedResourcePath = string.Format("{0}.Web.config.html", GetType().Namespace)
            }
        };
    }

    /// <summary>
    /// Sets the session manager and initializes PlaybackMonitor if not already initialized.
    /// </summary>
    /// <param name="sessionManager">The session manager.</param>
    public void SetSessionManager(ISessionManager sessionManager)
    {
        _sessionManager = sessionManager;
        
        // If SegmentStore is already initialized, create PlaybackMonitor
        if (_segmentStore != null && _playbackMonitor == null)
        {
            InitializePlaybackMonitor();
        }
    }

    /// <summary>
    /// Called when the plugin configuration is updated. Triggers segment reload to apply new settings.
    /// </summary>
    public override void UpdateConfiguration(BasePluginConfiguration configuration)
    {
        base.UpdateConfiguration(configuration);
        
        _logger.LogInformation("Plugin configuration updated - threshold changes will apply immediately to active playback sessions");
        
        // With the new dynamic filtering system, we don't need to reload segments from disk
        // The segments contain raw scores and filtering is applied dynamically based on current config
        // Active playback sessions will automatically use new thresholds on next boundary check
        
        // Optional: Force immediate re-evaluation of active sessions if playback monitor exists
        if (_playbackMonitor != null)
        {
            _logger.LogInformation("Configuration changed - active playback sessions will use new thresholds immediately");
        }
    }

    /// <summary>
    /// Manually triggers a reload of all segment data. Can be called after analysis tasks complete.
    /// </summary>
    /// <returns>Task representing the asynchronous operation.</returns>
    public async Task ReloadSegments()
    {
        if (_segmentStore != null)
        {
            await _segmentStore.ReloadAll();
        }
    }

    private void InitializeServices()
    {
        lock (this)
        {
            // Double-check after acquiring lock
            if (_segmentStore != null)
            {
                return;
            }

            try
            {
                _logger.LogInformation("Initializing Content Filter services");
                
                // Create a temporary logger factory if we don't have access to DI
                var loggerFactory = Microsoft.Extensions.Logging.LoggerFactory.Create(builder =>
                {
                    builder.AddConsole();
                });
                
                // Initialize segment store
                _segmentStore = new SegmentStore(loggerFactory.CreateLogger<SegmentStore>());
                _ = _segmentStore.LoadAll();
                
                _logger.LogInformation("Content Filter SegmentStore initialized successfully");
                
                // Initialize PlaybackMonitor if we have a session manager
                if (_sessionManager != null && _playbackMonitor == null)
                {
                    InitializePlaybackMonitor();
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error initializing Content Filter services");
            }
        }
    }

    private void InitializePlaybackMonitor()
    {
        lock (this)
        {
            if (_playbackMonitor != null || _sessionManager == null || _segmentStore == null)
            {
                return;
            }

            try
            {
                var loggerFactory = Microsoft.Extensions.Logging.LoggerFactory.Create(builder =>
                {
                    builder.AddConsole();
                });
                
                _playbackMonitor = new PlaybackMonitor(
                    _sessionManager,
                    _segmentStore,
                    loggerFactory.CreateLogger<PlaybackMonitor>());
                
                _logger.LogInformation("Content Filter PlaybackMonitor initialized successfully");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error initializing PlaybackMonitor");
            }
        }
    }

}
