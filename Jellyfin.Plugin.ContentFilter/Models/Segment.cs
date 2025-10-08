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
    /// Gets the raw AI confidence scores for all detected categories (0.0-1.0).
    /// These are the original AI model outputs before any threshold filtering.
    /// </summary>
    public Dictionary<string, double> RawScores { get; init; } = new();

    /// <summary>
    /// Gets the content categories (e.g., nudity, violence, profanity) that exceed current thresholds.
    /// This is computed dynamically based on current configuration settings.
    /// </summary>
    public string[] Categories { get; init; } = Array.Empty<string>();

    /// <summary>
    /// Gets the action to take (skip, mute, blur).
    /// </summary>
    public string Action { get; init; } = "skip";

    /// <summary>
    /// Gets the highest confidence score from RawScores (0.0-1.0).
    /// </summary>
    public double Confidence => RawScores.Values.DefaultIfEmpty(0.0).Max();

    /// <summary>
    /// Gets the source of the segment (ai, community, manual).
    /// </summary>
    public string Source { get; init; } = "ai";

    /// <summary>
    /// Gets the duration of the segment in seconds.
    /// </summary>
    public double Duration => End - Start;

    /// <summary>
    /// Determines if this segment should be filtered based on current configuration thresholds.
    /// </summary>
    /// <param name="config">Current plugin configuration with threshold settings.</param>
    /// <returns>True if any category exceeds its threshold and is enabled.</returns>
    public bool ShouldFilter(PluginConfiguration config)
    {
        if (!config.EnableNudity && !config.EnableImmodesty && 
            !config.EnableViolence && !config.EnableProfanity)
        {
            return false; // All filtering disabled
        }

        foreach (var (category, score) in RawScores)
        {
            switch (category.ToLowerInvariant())
            {
                case "nudity" when config.EnableNudity && score >= config.NudityThreshold:
                case "immodesty" when config.EnableImmodesty && score >= config.ImmodestyThreshold:
                case "violence" when config.EnableViolence && score >= config.ViolenceThreshold:
                case "general_violence" when config.EnableViolence && score >= config.ViolenceThreshold:
                case "extreme_violence" when config.EnableViolence && score >= config.ViolenceThreshold:
                case "profanity" when config.EnableProfanity && score >= config.ProfanityThreshold:
                    return true;
            }
        }

        return false;
    }

    /// <summary>
    /// Gets the categories that exceed current thresholds (for display/logging).
    /// </summary>
    /// <param name="config">Current plugin configuration with threshold settings.</param>
    /// <returns>Array of category names that exceed their thresholds.</returns>
    public string[] GetActiveCategories(PluginConfiguration config)
    {
        var activeCategories = new List<string>();

        foreach (var (category, score) in RawScores)
        {
            switch (category.ToLowerInvariant())
            {
                case "nudity" when config.EnableNudity && score >= config.NudityThreshold:
                    activeCategories.Add("nudity");
                    break;
                case "immodesty" when config.EnableImmodesty && score >= config.ImmodestyThreshold:
                    activeCategories.Add("immodesty");
                    break;
                case "violence" when config.EnableViolence && score >= config.ViolenceThreshold:
                case "general_violence" when config.EnableViolence && score >= config.ViolenceThreshold:
                case "extreme_violence" when config.EnableViolence && score >= config.ViolenceThreshold:
                    if (!activeCategories.Contains("violence"))
                        activeCategories.Add("violence");
                    break;
                case "profanity" when config.EnableProfanity && score >= config.ProfanityThreshold:
                    activeCategories.Add("profanity");
                    break;
            }
        }

        return activeCategories.ToArray();
    }
}
