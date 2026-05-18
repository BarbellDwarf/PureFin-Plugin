using System;
using System.Linq;
using Jellyfin.Database.Implementations.Enums;
using Jellyfin.Plugin.ContentFilter.Models;
using Jellyfin.Plugin.ContentFilter.Services;
using MediaBrowser.Controller.Entities;
using MediaBrowser.Controller.Library;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

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

    /// <summary>
    /// Initializes a new instance of the <see cref="PureFinSegmentsController"/> class.
    /// </summary>
    /// <param name="segmentStore">Segment store.</param>
    /// <param name="userManager">User manager.</param>
    /// <param name="libraryManager">Library manager.</param>
    public PureFinSegmentsController(
        SegmentStore segmentStore,
        IUserManager userManager,
        ILibraryManager libraryManager)
    {
        _segmentStore = segmentStore;
        _userManager = userManager;
        _libraryManager = libraryManager;
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
        var userId = GetUserId();
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
}
