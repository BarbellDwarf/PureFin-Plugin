using System;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Threading.Tasks;
using Jellyfin.Database.Implementations.Enums;
using Jellyfin.Plugin.ContentFilter.Models;
using Jellyfin.Plugin.ContentFilter.Services;
using MediaBrowser.Controller.Entities;
using MediaBrowser.Controller.Library;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.ContentFilter.Controllers;

/// <summary>
/// Admin-only endpoints for inspecting PureFin segment data.
/// </summary>
[ApiController]
[Authorize]
[Route("Plugins/PureFin")]
public class PureFinSegmentsController : ControllerBase
{
    private const string UserIdClaim = "Jellyfin-UserId";
    private readonly SegmentStore _segmentStore;
    private readonly IUserManager _userManager;
    private readonly ILibraryManager _libraryManager;
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<PureFinSegmentsController> _logger;

    /// <summary>
    /// Initializes a new instance of the <see cref="PureFinSegmentsController"/> class.
    /// </summary>
    /// <param name="segmentStore">Segment store.</param>
    /// <param name="userManager">User manager.</param>
    /// <param name="libraryManager">Library manager.</param>
    /// <param name="httpClientFactory">HTTP client factory.</param>
    /// <param name="logger">Logger.</param>
    public PureFinSegmentsController(
        SegmentStore segmentStore,
        IUserManager userManager,
        ILibraryManager libraryManager,
        IHttpClientFactory httpClientFactory,
        ILogger<PureFinSegmentsController> logger)
    {
        _segmentStore = segmentStore;
        _userManager = userManager;
        _libraryManager = libraryManager;
        _httpClientFactory = httpClientFactory;
        _logger = logger;
    }

    /// <summary>
    /// Gets PureFin segment data for a specific media item.
    /// </summary>
    /// <param name="itemId">The Jellyfin item ID.</param>
    /// <returns>Segment data for the media item.</returns>
    [HttpGet("Segments/{itemId}")]
    [ProducesResponseType(typeof(SegmentData), 200)]
    [ProducesResponseType(401)]
    [ProducesResponseType(403)]
    [ProducesResponseType(404)]
    public ActionResult<SegmentData> GetSegments([FromRoute] Guid itemId)
    {
        var authError = EnsureAdmin(out var userId);
        if (authError != null)
        {
            return authError;
        }

        var item = _libraryManager.GetItemById<BaseItem>(itemId, userId);
        if (item == null)
        {
            return NotFound();
        }

        var data = _segmentStore.Get(itemId.ToString());
        if (data == null)
        {
            return NotFound();
        }

        // Enrich segments with dynamic categories based on current config thresholds.
        var config = Plugin.Instance?.Configuration;
        if (config != null)
        {
            var enriched = new SegmentData
            {
                MediaId = data.MediaId,
                Version = data.Version,
                CreatedAt = data.CreatedAt,
                Segments = data.Segments.Select(s => EnrichSegment(s, config)).ToList()
            };
            return Ok(enriched);
        }

        return Ok(data);
    }

    /// <summary>
    /// Gets analysis queue status from the AI orchestrator.
    /// </summary>
    /// <returns>Queue status.</returns>
    [HttpGet("Queue/Status")]
    [ProducesResponseType(200)]
    [ProducesResponseType(401)]
    [ProducesResponseType(403)]
    [ProducesResponseType(503)]
    public Task<ActionResult> GetQueueStatus()
        => ForwardQueueRequestAsync("status", HttpMethod.Get);

    /// <summary>
    /// Pauses analysis queue processing.
    /// </summary>
    /// <param name="request">Optional pause reason.</param>
    /// <returns>Queue status after pause.</returns>
    [HttpPost("Queue/Pause")]
    [ProducesResponseType(200)]
    [ProducesResponseType(401)]
    [ProducesResponseType(403)]
    [ProducesResponseType(503)]
    public Task<ActionResult> PauseQueue([FromBody] QueuePauseRequest? request)
        => ForwardQueueRequestAsync(
            "pause",
            HttpMethod.Post,
            new { reason = string.IsNullOrWhiteSpace(request?.Reason) ? "Paused from Jellyfin UI" : request!.Reason });

    /// <summary>
    /// Resumes analysis queue processing.
    /// </summary>
    /// <returns>Queue status after resume.</returns>
    [HttpPost("Queue/Resume")]
    [ProducesResponseType(200)]
    [ProducesResponseType(401)]
    [ProducesResponseType(403)]
    [ProducesResponseType(503)]
    public Task<ActionResult> ResumeQueue()
        => ForwardQueueRequestAsync("resume", HttpMethod.Post);

    private static Segment EnrichSegment(Segment segment, Configuration.PluginConfiguration config)
    {
        return new Segment
        {
            Start = segment.Start,
            End = segment.End,
            RawScores = segment.RawScores,
            Categories = segment.GetActiveCategories(config),
            Action = segment.Action,
            Source = segment.Source
        };
    }

    private Guid GetUserId()
    {
        var claim = User.Claims.FirstOrDefault(c => c.Type.Equals(UserIdClaim, StringComparison.OrdinalIgnoreCase));
        return claim == null ? Guid.Empty : Guid.Parse(claim.Value);
    }

    private ActionResult? EnsureAdmin(out Guid userId)
    {
        userId = GetUserId();
        if (userId == Guid.Empty)
        {
            return Unauthorized();
        }

        var user = _userManager.GetUserById(userId);
        if (user == null)
        {
            return Unauthorized();
        }

        var isAdmin = user.Permissions.Any(permission =>
            permission.Kind == PermissionKind.IsAdministrator && permission.Value);
        if (!isAdmin)
        {
            return Forbid();
        }

        return null;
    }

    private async Task<ActionResult> ForwardQueueRequestAsync(string endpoint, HttpMethod method, object? payload = null)
    {
        var authError = EnsureAdmin(out _);
        if (authError != null)
        {
            return authError;
        }

        var baseUrl = Plugin.Instance?.Configuration?.AiServiceBaseUrl?.TrimEnd('/');
        if (string.IsNullOrWhiteSpace(baseUrl))
        {
            return StatusCode(503, new { error = "AI service base URL is not configured." });
        }

        var url = $"{baseUrl}/queue/{endpoint}";
        try
        {
            var client = _httpClientFactory.CreateClient();
            client.Timeout = TimeSpan.FromSeconds(15);

            using var request = new HttpRequestMessage(method, url);
            if (payload != null)
            {
                request.Content = JsonContent.Create(payload);
            }

            using var response = await client.SendAsync(request);
            var body = await response.Content.ReadAsStringAsync();
            try
            {
                var json = JsonSerializer.Deserialize<JsonElement>(body);
                return StatusCode((int)response.StatusCode, json);
            }
            catch (JsonException)
            {
                return StatusCode((int)response.StatusCode, new { raw = body });
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error calling AI queue endpoint {Endpoint}", endpoint);
            return StatusCode(503, new
            {
                error = "Could not communicate with AI queue service.",
                details = ex.Message
            });
        }
    }

    /// <summary>
    /// Request payload for pausing queue processing.
    /// </summary>
    public class QueuePauseRequest
    {
        /// <summary>
        /// Gets or sets optional pause reason.
        /// </summary>
        public string? Reason { get; set; }
    }
}
