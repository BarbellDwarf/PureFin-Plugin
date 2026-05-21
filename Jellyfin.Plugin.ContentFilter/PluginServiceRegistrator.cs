
using System;
using System.Threading;
using System.Threading.Tasks;
using Jellyfin.Plugin.ContentFilter.Services;
using Jellyfin.Plugin.ContentFilter.Tasks;
using MediaBrowser.Controller;
using MediaBrowser.Controller.Plugins;
using MediaBrowser.Controller.Session;
using MediaBrowser.Model.Tasks;
using Microsoft.Extensions.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.ContentFilter;

/// <summary>
/// Registers PureFin plugin services with Jellyfin's DI container.
/// </summary>
public class PluginServiceRegistrator : IPluginServiceRegistrator
{
    /// <inheritdoc />
    public void RegisterServices(IServiceCollection serviceCollection, IServerApplicationHost applicationHost)
    {
        serviceCollection.AddSingleton<SegmentStore>();
        serviceCollection.AddHttpClient();
        serviceCollection.AddHostedService<PluginEntryPoint>();
        serviceCollection.AddSingleton<IScheduledTask, AnalyzeLibraryTask>();
    }
}

/// <summary>
/// Hosted service for PureFin plugin initialization.
/// </summary>
public class PluginEntryPoint : IHostedService, IDisposable
{
    private readonly ILogger<PluginEntryPoint> _logger;
    private readonly ILoggerFactory _loggerFactory;
    private readonly ISessionManager _sessionManager;
    private readonly SegmentStore _segmentStore;
    private readonly IHttpClientFactory _httpClientFactory;
    private PlaybackMonitor? _playbackMonitor;
    private QueueAutoPauseCoordinator? _queueAutoPauseCoordinator;

    /// <summary>
    /// Initializes a new instance of the <see cref="PluginEntryPoint"/> class.
    /// </summary>
    /// <param name="loggerFactory">The logger factory.</param>
    /// <param name="sessionManager">The session manager.</param>
    /// <param name="segmentStore">The segment store.</param>
    public PluginEntryPoint(
        ILoggerFactory loggerFactory,
        ISessionManager sessionManager,
        SegmentStore segmentStore,
        IHttpClientFactory httpClientFactory)
    {
        _loggerFactory = loggerFactory;
        _sessionManager = sessionManager;
        _segmentStore = segmentStore;
        _httpClientFactory = httpClientFactory;
        _logger = loggerFactory.CreateLogger<PluginEntryPoint>();
    }

    /// <inheritdoc />
    public async Task StartAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("PureFin plugin starting up");

        try
        {
            await _segmentStore.LoadAll();

            _playbackMonitor = new PlaybackMonitor(
                _sessionManager,
                _segmentStore,
                _loggerFactory.CreateLogger<PlaybackMonitor>());

            _queueAutoPauseCoordinator = new QueueAutoPauseCoordinator(
                _sessionManager,
                _httpClientFactory,
                _loggerFactory.CreateLogger<QueueAutoPauseCoordinator>());

            _logger.LogInformation("PureFin plugin started successfully - SegmentStore, PlaybackMonitor, and QueueAutoPauseCoordinator initialized");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error starting PureFin plugin");
        }
    }

    /// <inheritdoc />
    public Task StopAsync(CancellationToken cancellationToken)
    {
        _logger.LogInformation("PureFin plugin stopping");

        try
        {
            _playbackMonitor?.Dispose();
            _playbackMonitor = null;
            _queueAutoPauseCoordinator?.Dispose();
            _queueAutoPauseCoordinator = null;
            _logger.LogInformation("PlaybackMonitor disposed");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error disposing PlaybackMonitor");
        }

        return Task.CompletedTask;
    }

    /// <inheritdoc />
    public void Dispose()
    {
        _playbackMonitor?.Dispose();
        _playbackMonitor = null;
        _queueAutoPauseCoordinator?.Dispose();
        _queueAutoPauseCoordinator = null;
    }
}
