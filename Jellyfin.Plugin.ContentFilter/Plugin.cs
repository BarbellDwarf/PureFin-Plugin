using System;
using System.Collections.Generic;
using Jellyfin.Plugin.ContentFilter.Configuration;
using Jellyfin.Plugin.ContentFilter.Services;
using MediaBrowser.Common.Configuration;
using MediaBrowser.Common.Plugins;
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
    private PlaybackMonitor? _playbackMonitor;
    private SegmentStore? _segmentStore;

    /// <summary>
    /// Initializes a new instance of the <see cref="Plugin"/> class.
    /// </summary>
    /// <param name="applicationPaths">Instance of the <see cref="IApplicationPaths"/> interface.</param>
    /// <param name="xmlSerializer">Instance of the <see cref="IXmlSerializer"/> interface.</param>
    /// <param name="loggerFactory">Logger factory.</param>
    public Plugin(
        IApplicationPaths applicationPaths,
        IXmlSerializer xmlSerializer,
        ILoggerFactory loggerFactory)
        : base(applicationPaths, xmlSerializer)
    {
        Instance = this;
        _logger = loggerFactory.CreateLogger<Plugin>();
        _logger.LogInformation("Content Filter Plugin initialized");
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
    public SegmentStore? SegmentStore => _segmentStore;

    /// <summary>
    /// Gets the playback monitor instance.
    /// </summary>
    public PlaybackMonitor? PlaybackMonitor => _playbackMonitor;

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
    /// Initialize plugin services.
    /// </summary>
    /// <param name="serviceProvider">Service provider.</param>
    public void Initialize(IServiceProvider serviceProvider)
    {
        try
        {
            var loggerFactory = serviceProvider.GetRequiredService<ILoggerFactory>();
            
            // Initialize segment store
            _segmentStore = new SegmentStore(loggerFactory.CreateLogger<SegmentStore>());
            _ = _segmentStore.LoadAll();
            
            // Initialize playback monitor
            var sessionManager = serviceProvider.GetRequiredService<MediaBrowser.Controller.Session.ISessionManager>();
            _playbackMonitor = new PlaybackMonitor(
                sessionManager,
                _segmentStore,
                loggerFactory.CreateLogger<PlaybackMonitor>());
            
            _logger.LogInformation("Content Filter services initialized successfully");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error initializing Content Filter services");
        }
    }

}
