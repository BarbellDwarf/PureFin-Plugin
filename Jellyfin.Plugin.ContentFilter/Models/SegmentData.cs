using System;
using System.Collections.Generic;

namespace Jellyfin.Plugin.ContentFilter.Models;

/// <summary>
/// Represents segment data for a media item.
/// </summary>
public record SegmentData
{
    /// <summary>
    /// Gets the media item ID.
    /// </summary>
    public string MediaId { get; init; } = string.Empty;

    /// <summary>
    /// Gets the version number.
    /// </summary>
    public int Version { get; init; } = 1;

    /// <summary>
    /// Gets the segments.
    /// </summary>
    public IReadOnlyList<Segment> Segments { get; init; } = Array.Empty<Segment>();

    /// <summary>
    /// Gets the timestamp when this data was created.
    /// </summary>
    public DateTime CreatedAt { get; init; } = DateTime.UtcNow;

    /// <summary>
    /// Gets the media file hash for change detection.
    /// </summary>
    public string? FileHash { get; init; }
}
