using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text.Json;
using System.Text.Json.Nodes;
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
    /// Updates PureFin segment data for a specific media item.
    /// </summary>
    /// <param name="itemId">The Jellyfin item ID.</param>
    /// <param name="request">Updated segment payload.</param>
    /// <returns>Saved segment data for the media item.</returns>
    [HttpPut("Segments/{itemId}")]
    [ProducesResponseType(typeof(SegmentData), 200)]
    [ProducesResponseType(400)]
    [ProducesResponseType(401)]
    [ProducesResponseType(403)]
    [ProducesResponseType(404)]
    public async Task<ActionResult<SegmentData>> UpdateSegments([FromRoute] Guid itemId, [FromBody] SegmentUpdateRequest request)
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

        if (request == null || request.Segments == null)
        {
            return BadRequest(new { error = "Segments payload is required." });
        }

        var normalizedSegments = new List<Segment>(request.Segments.Count);
        foreach (var requestedSegment in request.Segments)
        {
            if (requestedSegment.End <= requestedSegment.Start)
            {
                return BadRequest(new { error = "Each segment must have end > start." });
            }

            if (requestedSegment.Start < 0)
            {
                return BadRequest(new { error = "Segment start must be >= 0." });
            }

            var source = string.IsNullOrWhiteSpace(requestedSegment.Source)
                ? "manual"
                : requestedSegment.Source.Trim();
            var rawScores = NormalizeRawScores(requestedSegment.RawScores, source);
            normalizedSegments.Add(new Segment
            {
                Start = requestedSegment.Start,
                End = requestedSegment.End,
                Action = string.IsNullOrWhiteSpace(requestedSegment.Action) ? "skip" : requestedSegment.Action.Trim(),
                Source = source,
                RawScores = rawScores
            });
        }

        var mediaId = itemId.ToString();
        var existing = _segmentStore.Get(mediaId);
        var saved = new SegmentData
        {
            MediaId = mediaId,
            Version = (existing?.Version ?? 0) + 1,
            CreatedAt = DateTime.UtcNow,
            FileHash = existing?.FileHash,
            Segments = normalizedSegments.OrderBy(segment => segment.Start).ToList()
        };

        await _segmentStore.Put(mediaId, saved);
        var config = Plugin.Instance?.Configuration;
        if (config == null)
        {
            return Ok(saved);
        }

        return Ok(new SegmentData
        {
            MediaId = saved.MediaId,
            Version = saved.Version,
            CreatedAt = saved.CreatedAt,
            FileHash = saved.FileHash,
            Segments = saved.Segments.Select(segment => EnrichSegment(segment, config)).ToList()
        });
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
    public Task<ActionResult> GetQueueStatus([FromQuery] string? host = null)
        => ForwardQueueRequestAsync("status", HttpMethod.Get, host: host);

    /// <summary>
    /// Pauses analysis queue processing.
    /// </summary>
    /// <param name="request">Optional pause reason.</param>
    /// <param name="host">Optional specific host base URL to target.</param>
    /// <returns>Queue status after pause.</returns>
    [HttpPost("Queue/Pause")]
    [ProducesResponseType(200)]
    [ProducesResponseType(401)]
    [ProducesResponseType(403)]
    [ProducesResponseType(503)]
    public Task<ActionResult> PauseQueue([FromBody] QueuePauseRequest? request, [FromQuery] string? host = null)
        => ForwardQueueRequestAsync(
            "pause",
            HttpMethod.Post,
            new { reason = string.IsNullOrWhiteSpace(request?.Reason) ? "Paused from Jellyfin UI" : request!.Reason },
            host);

    /// <summary>
    /// Resumes analysis queue processing.
    /// </summary>
    /// <returns>Queue status after resume.</returns>
    [HttpPost("Queue/Resume")]
    [ProducesResponseType(200)]
    [ProducesResponseType(401)]
    [ProducesResponseType(403)]
    [ProducesResponseType(503)]
    public Task<ActionResult> ResumeQueue([FromQuery] string? host = null)
        => ForwardQueueRequestAsync("resume", HttpMethod.Post, host: host);

    /// <summary>
    /// Gets AI service runtime/model status for all configured hosts.
    /// </summary>
    /// <param name="host">Optional specific host base URL to query.</param>
    /// <returns>Per-host runtime and model metadata.</returns>
    [HttpGet("AiServices/Status")]
    [ProducesResponseType(200)]
    [ProducesResponseType(401)]
    [ProducesResponseType(403)]
    [ProducesResponseType(503)]
    public async Task<ActionResult> GetAiServicesStatus([FromQuery] string? host = null)
    {
        var authError = EnsureAdmin(out _);
        if (authError != null)
        {
            return authError;
        }

        var config = Plugin.Instance?.Configuration;
        if (config == null)
        {
            return StatusCode(503, new { error = "Plugin configuration is not available." });
        }

        var endpoints = ResolveTargetHosts(config, host);
        if (endpoints.Count == 0)
        {
            return StatusCode(503, new { error = "No valid AI service endpoints configured." });
        }

        var client = _httpClientFactory.CreateClient();
        client.Timeout = TimeSpan.FromSeconds(15);
        var hostStatuses = await Task.WhenAll(endpoints.Select(endpoint => QueryRuntimeStatusAsync(client, endpoint)));
        var successCount = hostStatuses.Count(result => result.Success);
        if (successCount == 0)
        {
            return StatusCode(503, new
            {
                success = false,
                error = "Could not communicate with any configured AI service host.",
                hosts = hostStatuses
            });
        }

        return Ok(new
        {
            success = true,
            load_balancing_mode = config.AiServiceLoadBalancingMode,
            configured_hosts = endpoints.Count,
            successful_hosts = successCount,
            failed_hosts = endpoints.Count - successCount,
            hosts = hostStatuses
        });
    }

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
        var preferredClaimTypes = new[]
        {
            UserIdClaim,
            "UserId",
            ClaimTypes.NameIdentifier,
            "sub"
        };

        foreach (var claimType in preferredClaimTypes)
        {
            var claim = User.Claims.FirstOrDefault(c => c.Type.Equals(claimType, StringComparison.OrdinalIgnoreCase));
            if (claim != null && Guid.TryParse(claim.Value, out var parsed))
            {
                return parsed;
            }
        }

        var fallbackClaim = User.Claims.FirstOrDefault(c =>
            c.Type.Contains("userid", StringComparison.OrdinalIgnoreCase) &&
            Guid.TryParse(c.Value, out _));

        if (fallbackClaim != null && Guid.TryParse(fallbackClaim.Value, out var fallback))
        {
            return fallback;
        }

        return Guid.Empty;
    }

    private bool HasAdminClaim()
    {
        return User.Claims.Any(claim =>
        {
            var isAdminClaimType =
                claim.Type.Contains("administrator", StringComparison.OrdinalIgnoreCase) ||
                claim.Type.Contains("admin", StringComparison.OrdinalIgnoreCase) ||
                claim.Type.EndsWith("role", StringComparison.OrdinalIgnoreCase);

            if (!isAdminClaimType)
            {
                return false;
            }

            return claim.Value.Equals("true", StringComparison.OrdinalIgnoreCase) ||
                   claim.Value.Contains("admin", StringComparison.OrdinalIgnoreCase);
        });
    }

    private ActionResult? EnsureAdmin(out Guid userId)
    {
        userId = GetUserId();
        if (userId == Guid.Empty)
        {
            return HasAdminClaim() ? null : Unauthorized();
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

    private async Task<ActionResult> ForwardQueueRequestAsync(string endpoint, HttpMethod method, object? payload = null, string? host = null)
    {
        var authError = EnsureAdmin(out _);
        if (authError != null)
        {
            return authError;
        }

        var config = Plugin.Instance?.Configuration;
        if (config == null)
        {
            return StatusCode(503, new { error = "Plugin configuration is not available." });
        }

        var endpoints = ResolveTargetHosts(config, host);
        if (endpoints.Count == 0)
        {
            return StatusCode(503, new { error = "No valid AI service endpoints configured." });
        }

        try
        {
            var client = _httpClientFactory.CreateClient();
            client.Timeout = TimeSpan.FromSeconds(15);

            var hostResults = await Task.WhenAll(endpoints.Select(async endpointBase =>
            {
                var runtime = await QueryRuntimeStatusAsync(client, endpointBase);
                var queue = await QueryQueueEndpointAsync(client, endpointBase, endpoint, method, payload);
                return new HostQueueResult
                {
                    BaseUrl = endpointBase,
                    Runtime = runtime,
                    Queue = queue
                };
            }));

            var succeeded = hostResults.Where(result => result.Queue.Success).ToList();
            if (succeeded.Count == 0)
            {
                return StatusCode(503, new
                {
                    success = false,
                    error = $"Queue {endpoint} failed on all configured AI hosts.",
                    hosts = hostResults
                });
            }

            var queuePayloads = succeeded
                .Select(result => result.Queue.Payload)
                .Where(static payloadNode => payloadNode is not null)
                .Cast<JsonObject>()
                .ToList();

            var pausedHosts = queuePayloads.Count(payloadNode => ReadBool(payloadNode, "paused"));
            var pauseReasons = queuePayloads
                .Select(payloadNode => ReadString(payloadNode, "pause_reason"))
                .Where(reason => !string.IsNullOrWhiteSpace(reason))
                .Distinct(StringComparer.Ordinal)
                .ToArray();

            var pendingJobs = queuePayloads.Sum(payloadNode => ReadInt(payloadNode, "pending_jobs"));
            var activeJobs = queuePayloads.Sum(payloadNode => ReadInt(payloadNode, "active_jobs"));
            var processedJobs = queuePayloads.Sum(payloadNode => ReadInt(payloadNode, "processed_jobs"));
            var failedJobs = queuePayloads.Sum(payloadNode => ReadInt(payloadNode, "failed_jobs"));
            var unloadSeconds = queuePayloads
                .Select(payloadNode => ReadNullableInt(payloadNode, "model_idle_unload_seconds"))
                .Where(static value => value.HasValue)
                .Select(static value => value!.Value)
                .Distinct()
                .ToArray();

            return Ok(new
            {
                success = true,
                endpoint,
                load_balancing_mode = config.AiServiceLoadBalancingMode,
                configured_hosts = endpoints.Count,
                successful_hosts = succeeded.Count,
                failed_hosts = endpoints.Count - succeeded.Count,
                paused = queuePayloads.Count > 0 && pausedHosts == queuePayloads.Count,
                partially_paused = pausedHosts > 0 && pausedHosts < queuePayloads.Count,
                pause_reason = pauseReasons.Length == 0 ? null : string.Join("; ", pauseReasons),
                pending_jobs = pendingJobs,
                active_jobs = activeJobs,
                processed_jobs = processedJobs,
                failed_jobs = failedJobs,
                model_idle_unload_seconds = unloadSeconds.Length == 1 ? unloadSeconds[0] : (int?)null,
                hosts = hostResults
            });
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

    private static IReadOnlyList<string> ResolveTargetHosts(Configuration.PluginConfiguration configuration, string? requestedHost)
    {
        var allHosts = AiServiceEndpointHelper.GetConfiguredBaseUrls(configuration);
        if (string.IsNullOrWhiteSpace(requestedHost))
        {
            return allHosts;
        }

        if (!Uri.TryCreate(requestedHost, UriKind.Absolute, out var requestedUri))
        {
            return Array.Empty<string>();
        }

        var normalized = requestedUri.ToString().TrimEnd('/');
        return allHosts.Where(host => string.Equals(host, normalized, StringComparison.OrdinalIgnoreCase)).ToList();
    }

    private async Task<HostRuntimeResult> QueryRuntimeStatusAsync(HttpClient client, string baseUrl)
    {
        var health = await SendJsonRequestAsync(client, $"{baseUrl}/health", HttpMethod.Get, null);
        var ready = await SendJsonRequestAsync(client, $"{baseUrl}/ready", HttpMethod.Get, null);

        var downstream = ReadObject(health.Payload, "downstream");
        var violence = ReadObject(downstream, "violence_detector");

        return new HostRuntimeResult
        {
            BaseUrl = baseUrl,
            Success = health.Success || ready.Success,
            HealthStatusCode = health.StatusCode,
            ReadyStatusCode = ready.StatusCode,
            Ready = ReadBool(ready.Payload, "ready")
                || string.Equals(ReadString(ready.Payload, "status"), "ready", StringComparison.OrdinalIgnoreCase),
            ModelProfile = ReadString(violence, "model_profile"),
            ModelId = ReadString(violence, "model_id") ?? ReadString(health.Payload, "violence_model_id"),
            Device = ReadString(violence, "device"),
            Health = health.Payload,
            ReadyPayload = ready.Payload,
            Error = health.Error ?? ready.Error
        };
    }

    private async Task<HostQueueEndpointResult> QueryQueueEndpointAsync(
        HttpClient client,
        string baseUrl,
        string endpoint,
        HttpMethod method,
        object? payload)
    {
        var response = await SendJsonRequestAsync(client, $"{baseUrl}/queue/{endpoint}", method, payload);
        return new HostQueueEndpointResult
        {
            Success = response.Success,
            StatusCode = response.StatusCode,
            Payload = response.Payload,
            Error = response.Error
        };
    }

    private async Task<JsonRequestResult> SendJsonRequestAsync(HttpClient client, string url, HttpMethod method, object? payload)
    {
        try
        {
            using var request = new HttpRequestMessage(method, url);
            if (payload != null)
            {
                request.Content = JsonContent.Create(payload);
            }

            using var response = await client.SendAsync(request);
            var rawBody = await response.Content.ReadAsStringAsync();
            JsonObject? jsonPayload = null;
            if (!string.IsNullOrWhiteSpace(rawBody))
            {
                try
                {
                    jsonPayload = JsonNode.Parse(rawBody) as JsonObject;
                }
                catch (JsonException)
                {
                    jsonPayload = new JsonObject
                    {
                        ["raw"] = rawBody
                    };
                }
            }

            return new JsonRequestResult
            {
                Success = response.IsSuccessStatusCode,
                StatusCode = (int)response.StatusCode,
                Payload = jsonPayload,
                Error = response.IsSuccessStatusCode ? null : ReadString(jsonPayload, "error") ?? $"HTTP {(int)response.StatusCode}"
            };
        }
        catch (Exception ex)
        {
            return new JsonRequestResult
            {
                Success = false,
                StatusCode = null,
                Payload = null,
                Error = ex.Message
            };
        }
    }

    private static JsonObject? ReadObject(JsonObject? source, string propertyName)
    {
        return source?[propertyName] as JsonObject;
    }

    private static string? ReadString(JsonObject? source, string propertyName)
    {
        var valueNode = source?[propertyName];
        return valueNode is JsonValue jsonValue && jsonValue.TryGetValue(out string? value) ? value : null;
    }

    private static bool ReadBool(JsonObject? source, string propertyName)
    {
        var valueNode = source?[propertyName];
        return valueNode is JsonValue jsonValue && jsonValue.TryGetValue(out bool value) && value;
    }

    private static int ReadInt(JsonObject? source, string propertyName)
    {
        var valueNode = source?[propertyName];
        return valueNode is JsonValue jsonValue && jsonValue.TryGetValue(out int value) ? value : 0;
    }

    private static int? ReadNullableInt(JsonObject? source, string propertyName)
    {
        var valueNode = source?[propertyName];
        if (valueNode is JsonValue jsonValue && jsonValue.TryGetValue(out int value))
        {
            return value;
        }

        return null;
    }

    private sealed class JsonRequestResult
    {
        public bool Success { get; set; }

        public int? StatusCode { get; set; }

        public JsonObject? Payload { get; set; }

        public string? Error { get; set; }
    }

    private sealed class HostRuntimeResult
    {
        public string BaseUrl { get; set; } = string.Empty;

        public bool Success { get; set; }

        public int? HealthStatusCode { get; set; }

        public int? ReadyStatusCode { get; set; }

        public bool Ready { get; set; }

        public string? ModelProfile { get; set; }

        public string? ModelId { get; set; }

        public string? Device { get; set; }

        public JsonObject? Health { get; set; }

        public JsonObject? ReadyPayload { get; set; }

        public string? Error { get; set; }
    }

    private sealed class HostQueueEndpointResult
    {
        public bool Success { get; set; }

        public int? StatusCode { get; set; }

        public JsonObject? Payload { get; set; }

        public string? Error { get; set; }
    }

    private sealed class HostQueueResult
    {
        public string BaseUrl { get; set; } = string.Empty;

        public HostRuntimeResult Runtime { get; set; } = new();

        public HostQueueEndpointResult Queue { get; set; } = new();
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

    /// <summary>
    /// Segment update payload.
    /// </summary>
    public sealed class SegmentUpdateRequest
    {
        /// <summary>
        /// Gets or sets the segments to persist.
        /// </summary>
        public List<SegmentUpdateItem>? Segments { get; set; }
    }

    /// <summary>
    /// Segment update item payload.
    /// </summary>
    public sealed class SegmentUpdateItem
    {
        /// <summary>
        /// Gets or sets segment start in seconds.
        /// </summary>
        public double Start { get; set; }

        /// <summary>
        /// Gets or sets segment end in seconds.
        /// </summary>
        public double End { get; set; }

        /// <summary>
        /// Gets or sets action type.
        /// </summary>
        public string? Action { get; set; }

        /// <summary>
        /// Gets or sets segment source.
        /// </summary>
        public string? Source { get; set; }

        /// <summary>
        /// Gets or sets raw category scores.
        /// </summary>
        public Dictionary<string, double>? RawScores { get; set; }
    }

    private static Dictionary<string, double> NormalizeRawScores(Dictionary<string, double>? rawScores, string source)
    {
        if (rawScores == null || rawScores.Count == 0)
        {
            return string.Equals(source, "manual", StringComparison.OrdinalIgnoreCase)
                ? new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase) { ["manual"] = 1.0 }
                : new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase);
        }

        var normalized = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase);
        foreach (var (key, value) in rawScores)
        {
            if (string.IsNullOrWhiteSpace(key) || double.IsNaN(value) || double.IsInfinity(value))
            {
                continue;
            }

            normalized[key.Trim()] = Math.Clamp(value, 0.0, 1.0);
        }

        if (normalized.Count == 0 && string.Equals(source, "manual", StringComparison.OrdinalIgnoreCase))
        {
            normalized["manual"] = 1.0;
        }

        return normalized;
    }
}
