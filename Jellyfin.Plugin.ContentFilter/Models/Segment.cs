using System;

namespace Jellyfin.Plugin.ContentFilter.Models;

/// <summary>
/// Represents a content filter segment with timing and category information.
/// </summary>
public record Segment
{
    /// <summary>
    /// Gets the start time in seconds.
    /// </summary>
    public double Start { get; init; }

    /// <summary>
    /// Gets the end time in seconds.
    /// </summary>
    public double End { get; init; }

    /// <summary>
    /// Gets the content categories (e.g., nudity, violence, profanity).
    /// </summary>
    public string[] Categories { get; init; } = Array.Empty<string>();

    /// <summary>
    /// Gets the action to take (skip, mute, blur).
    /// </summary>
    public string Action { get; init; } = "skip";

    /// <summary>
    /// Gets the confidence score (0.0-1.0).
    /// </summary>
    public double Confidence { get; init; }

    /// <summary>
    /// Gets the source of the segment (ai, community, manual).
    /// </summary>
    public string Source { get; init; } = "ai";

    /// <summary>
    /// Gets the duration of the segment in seconds.
    /// </summary>
    public double Duration => End - Start;
}
