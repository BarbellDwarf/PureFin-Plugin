using System;
using System.Collections.Concurrent;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Jellyfin.Plugin.ContentFilter.Models;
using MediaBrowser.Controller.Session;
using MediaBrowser.Model.Session;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.ContentFilter.Services;

/// <summary>
/// Monitors playback sessions and applies content filtering.
/// </summary>
public class PlaybackMonitor : IDisposable
{
    private readonly ISessionManager _sessionManager;
    private readonly SegmentStore _segmentStore;
    private readonly ILogger<PlaybackMonitor> _logger;
    private readonly ConcurrentDictionary<string, SessionState> _sessions = new();
    private readonly Timer _monitorTimer;
    private bool _disposed;

    /// <summary>
    /// Initializes a new instance of the <see cref="PlaybackMonitor"/> class.
    /// </summary>
    /// <param name="sessionManager">Session manager.</param>
    /// <param name="segmentStore">Segment store.</param>
    /// <param name="logger">Logger.</param>
    public PlaybackMonitor(
        ISessionManager sessionManager,
        SegmentStore segmentStore,
        ILogger<PlaybackMonitor> logger)
    {
        _sessionManager = sessionManager;
        _segmentStore = segmentStore;
        _logger = logger;

        // Start monitoring timer (checks every 500ms)
        _monitorTimer = new Timer(MonitorSessions, null, TimeSpan.FromMilliseconds(500), TimeSpan.FromMilliseconds(500));

        _logger.LogInformation("Playback monitor started");
    }

    /// <inheritdoc />
    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _monitorTimer?.Dispose();
        _disposed = true;

        _logger.LogInformation("Playback monitor stopped");
    }

    private void MonitorSessions(object? state)
    {
        // Monitor all active playback sessions
        var activeSessions = _sessionManager.Sessions
            .Where(s => s.NowPlayingItem != null && s.PlayState?.PositionTicks != null)
            .ToList();

        foreach (var session in activeSessions)
        {
            try
            {
                var sessionId = session.Id;
                var mediaId = session.NowPlayingItem!.Id.ToString();
                var positionTicks = session.PlayState!.PositionTicks!.Value;
                var positionSeconds = TimeSpan.FromTicks(positionTicks).TotalSeconds;

                // Get or create session state
                var sessionState = _sessions.GetOrAdd(sessionId, _ => new SessionState
                {
                    SessionId = sessionId,
                    MediaId = mediaId,
                    LastPosition = positionSeconds,
                    ActiveSegment = null
                });

                // Update position
                sessionState.MediaId = mediaId;
                sessionState.LastPosition = positionSeconds;

                // Check for segment boundary
                CheckForSegmentBoundary(sessionState);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error monitoring session {SessionId}", session.Id);
            }
        }
    }

    private void CheckForSegmentBoundary(SessionState state)
    {
        var config = Plugin.Instance?.Configuration;
        if (config == null)
        {
            return;
        }

        var activeSegments = _segmentStore.GetActiveSegments(state.MediaId, state.LastPosition);

        // Filter segments based on current configuration thresholds
        var filterableSegment = activeSegments.FirstOrDefault(segment => segment.ShouldFilter(config));

        // Check if we entered a new segment that should be filtered
        if (filterableSegment != null && !Equals(filterableSegment, state.ActiveSegment))
        {
            state.ActiveSegment = filterableSegment;
            _ = ApplyFilterAction(state, filterableSegment);
        }
        // Check if we left a segment or current segment no longer meets threshold
        else if (filterableSegment == null && state.ActiveSegment != null)
        {
            state.ActiveSegment = null;
        }
    }

    private async Task ApplyFilterAction(SessionState state, Segment segment)
    {
        var config = Plugin.Instance?.Configuration;
        if (config == null)
        {
            return;
        }

        // Get active categories based on current configuration
        var activeCategories = segment.GetActiveCategories(config);
        
        _logger.LogInformation(
            "Applying filter action: Session={SessionId}, Action={Action}, Categories={Categories}, RawScores={RawScores}",
            state.SessionId,
            segment.Action,
            string.Join(", ", activeCategories),
            string.Join(", ", segment.RawScores.Select(kvp => $"{kvp.Key}:{kvp.Value:F2}")));

        try
        {
            var jellyfinSession = _sessionManager.Sessions.FirstOrDefault(s => s.Id == state.SessionId);
            if (jellyfinSession == null)
            {
                _logger.LogWarning("Session not found: {SessionId}", state.SessionId);
                return;
            }

            switch (segment.Action.ToLowerInvariant())
            {
                case "skip":
                    // Seek to end of segment
                    var seekCommand = new PlaystateRequest
                    {
                        Command = PlaystateCommand.Seek,
                        SeekPositionTicks = (long)(segment.End * TimeSpan.TicksPerSecond)
                    };
                    await _sessionManager.SendPlaystateCommand(
                        jellyfinSession.Id,
                        jellyfinSession.Id,
                        seekCommand,
                        CancellationToken.None);
                    break;

                case "mute":
                    // Mute audio (if supported by client)
                    // This is a simplified implementation
                    _logger.LogInformation("Mute action requested but not fully implemented");
                    break;

                default:
                    _logger.LogWarning("Unknown action: {Action}", segment.Action);
                    break;
            }

            // Show OSD feedback if enabled
            if (config.EnableOsdFeedback)
            {
                var message = $"Content Filtered: {string.Join(", ", activeCategories)}";
                await _sessionManager.SendMessageCommand(
                    jellyfinSession.Id,
                    jellyfinSession.Id,
                    new MessageCommand
                    {
                        Header = "Content Filter",
                        Text = message,
                        TimeoutMs = 3000
                    },
                    CancellationToken.None);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error applying filter action for session {SessionId}", state.SessionId);
        }
    }

    private class SessionState
    {
        public string MediaId { get; set; } = string.Empty;
        public string SessionId { get; set; } = string.Empty;
        public double LastPosition { get; set; }
        public Segment? ActiveSegment { get; set; }
    }
}
