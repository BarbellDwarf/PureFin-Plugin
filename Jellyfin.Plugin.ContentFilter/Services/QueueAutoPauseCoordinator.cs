using System;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading;
using System.Threading.Tasks;
using Jellyfin.Plugin.ContentFilter.Configuration;
using MediaBrowser.Controller.Session;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.ContentFilter.Services;

/// <summary>
/// Automatically pauses/resumes AI analysis queue processing while Jellyfin is transcoding.
/// </summary>
public sealed class QueueAutoPauseCoordinator : IDisposable
{
    private static readonly TimeSpan PollInterval = TimeSpan.FromSeconds(5);
    private const string AutoPauseReason = "Paused automatically by PureFin while Jellyfin transcoding is active";

    private readonly ISessionManager _sessionManager;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<QueueAutoPauseCoordinator> _logger;
    private readonly Timer _timer;
    private readonly SemaphoreSlim _pollGate = new(1, 1);
    private bool _disposed;
    private bool _autoPauseApplied;

    /// <summary>
    /// Initializes a new instance of the <see cref="QueueAutoPauseCoordinator"/> class.
    /// </summary>
    /// <param name="sessionManager">Session manager.</param>
    /// <param name="httpClientFactory">HTTP client factory.</param>
    /// <param name="logger">Logger.</param>
    public QueueAutoPauseCoordinator(
        ISessionManager sessionManager,
        IHttpClientFactory httpClientFactory,
        ILogger<QueueAutoPauseCoordinator> logger)
    {
        _sessionManager = sessionManager;
        _httpClientFactory = httpClientFactory;
        _logger = logger;
        _timer = new Timer(TimerTick, null, PollInterval, PollInterval);
    }

    /// <inheritdoc />
    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;
        _timer.Dispose();
        _pollGate.Dispose();
    }

    private void TimerTick(object? _)
    {
        _ = PollAsync();
    }

    private async Task PollAsync()
    {
        if (_disposed || !await _pollGate.WaitAsync(0))
        {
            return;
        }

        try
        {
            var config = Plugin.Instance?.Configuration;
            if (config == null)
            {
                return;
            }

            if (!config.AutoPauseQueueDuringTranscoding)
            {
                if (_autoPauseApplied)
                {
                    var resumed = await ResumeQueuesAsync(config);
                    if (resumed)
                    {
                        _autoPauseApplied = false;
                        _logger.LogInformation("Auto-paused analysis queues resumed because transcode auto-pause setting was disabled");
                    }
                }

                return;
            }

            var hasActiveTranscode = _sessionManager.Sessions.Any(session =>
                session.NowPlayingItem != null &&
                session.TranscodingInfo != null);

            if (hasActiveTranscode && !_autoPauseApplied)
            {
                var paused = await PauseQueuesAsync(config);
                if (paused)
                {
                    _autoPauseApplied = true;
                    _logger.LogInformation("AI analysis queues auto-paused due to active Jellyfin transcoding sessions");
                }
            }
            else if (!hasActiveTranscode && _autoPauseApplied)
            {
                var resumed = await ResumeQueuesAsync(config);
                if (resumed)
                {
                    _autoPauseApplied = false;
                    _logger.LogInformation("AI analysis queues auto-resumed because no active Jellyfin transcoding sessions remain");
                }
            }
        }
        finally
        {
            _pollGate.Release();
        }
    }

    private async Task<bool> PauseQueuesAsync(PluginConfiguration config)
    {
        var hosts = AiServiceEndpointHelper.GetConfiguredBaseUrls(config);
        if (hosts.Count == 0)
        {
            _logger.LogWarning("Cannot auto-pause AI queue: no configured AI service hosts");
            return false;
        }

        var client = _httpClientFactory.CreateClient();
        client.Timeout = TimeSpan.FromSeconds(10);

        var successful = 0;
        foreach (var host in hosts)
        {
            using var request = new HttpRequestMessage(HttpMethod.Post, $"{host}/queue/pause")
            {
                Content = JsonContent.Create(new { reason = AutoPauseReason })
            };

            try
            {
                using var response = await client.SendAsync(request);
                if (response.IsSuccessStatusCode)
                {
                    successful++;
                }
                else
                {
                    _logger.LogWarning("Auto-pause request failed for {Host} with status {StatusCode}", host, (int)response.StatusCode);
                }
            }
            catch (HttpRequestException ex)
            {
                _logger.LogWarning(ex, "Auto-pause request failed for {Host}", host);
            }
            catch (TaskCanceledException ex)
            {
                _logger.LogWarning(ex, "Auto-pause request timed out for {Host}", host);
            }
        }

        return successful > 0;
    }

    private async Task<bool> ResumeQueuesAsync(PluginConfiguration config)
    {
        var hosts = AiServiceEndpointHelper.GetConfiguredBaseUrls(config);
        if (hosts.Count == 0)
        {
            _logger.LogWarning("Cannot auto-resume AI queue: no configured AI service hosts");
            return false;
        }

        var client = _httpClientFactory.CreateClient();
        client.Timeout = TimeSpan.FromSeconds(10);

        var successful = 0;
        foreach (var host in hosts)
        {
            using var request = new HttpRequestMessage(HttpMethod.Post, $"{host}/queue/resume");

            try
            {
                using var response = await client.SendAsync(request);
                if (response.IsSuccessStatusCode)
                {
                    successful++;
                }
                else
                {
                    _logger.LogWarning("Auto-resume request failed for {Host} with status {StatusCode}", host, (int)response.StatusCode);
                }
            }
            catch (HttpRequestException ex)
            {
                _logger.LogWarning(ex, "Auto-resume request failed for {Host}", host);
            }
            catch (TaskCanceledException ex)
            {
                _logger.LogWarning(ex, "Auto-resume request timed out for {Host}", host);
            }
        }

        return successful > 0;
    }
}
