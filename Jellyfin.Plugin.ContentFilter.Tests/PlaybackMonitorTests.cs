using System.Collections.Generic;
using Jellyfin.Plugin.ContentFilter.Configuration;
using Jellyfin.Plugin.ContentFilter.Models;
using Xunit;

namespace Jellyfin.Plugin.ContentFilter.Tests;

/// <summary>
/// Tests for PlaybackMonitor's filtering logic via the Segment model.
/// PlaybackMonitor itself depends on Jellyfin's ISessionManager and Plugin.Instance
/// static state, which are not available in unit tests. These tests verify the
/// threshold / action dispatch logic that PlaybackMonitor delegates to the Segment model.
/// </summary>
public class PlaybackMonitorTests
{
    private static PluginConfiguration MakeConfig(
        string sensitivity = "moderate",
        bool nudity = true,
        bool violence = true,
        bool profanity = true)
    {
        var base_ = new PluginConfiguration
        {
            Sensitivity = sensitivity,
            EnableNudity = nudity,
            EnableViolence = violence,
            EnableProfanity = profanity,
            EnableImmodesty = true
        };
        return base_.WithSensitivityThresholds();
    }

    // ---------------------------------------------------------------
    // Threshold tests — segments below threshold are NOT triggered
    // ---------------------------------------------------------------

    [Fact]
    public void SegmentBelowThreshold_ShouldNotFilter()
    {
        var config = MakeConfig("moderate"); // NSFW threshold = 0.65
        var segment = new Segment
        {
            Start = 0.0,
            End = 10.0,
            Action = "skip",
            RawScores = new Dictionary<string, double> { ["nudity"] = 0.50 }
        };

        Assert.False(segment.ShouldFilter(config));
    }

    [Fact]
    public void SegmentAtThreshold_ShouldFilter()
    {
        var config = MakeConfig("moderate"); // NSFW threshold = 0.65
        var segment = new Segment
        {
            Start = 0.0,
            End = 10.0,
            Action = "skip",
            RawScores = new Dictionary<string, double> { ["nudity"] = 0.65, ["immodesty"] = 0.10 }
        };

        Assert.True(segment.ShouldFilter(config));
    }

    [Fact]
    public void SegmentAboveThreshold_ShouldFilter()
    {
        var config = MakeConfig("moderate"); // NSFW threshold = 0.65
        var segment = new Segment
        {
            Start = 0.0,
            End = 10.0,
            Action = "skip",
            RawScores = new Dictionary<string, double> { ["nudity"] = 0.90, ["immodesty"] = 0.10 }
        };

        Assert.True(segment.ShouldFilter(config));
    }

    // ---------------------------------------------------------------
    // Mute action — segment is still filterable (fallback is in monitor)
    // ---------------------------------------------------------------

    [Fact]
    public void MuteActionSegment_AboveThreshold_ShouldFilter()
    {
        // The mute-to-skip fallback happens in PlaybackMonitor.ApplyFilterAction.
        // ShouldFilter() only checks score vs. threshold — action type is irrelevant here.
        var config = MakeConfig("moderate");
        var segment = new Segment
        {
            Start = 5.0,
            End = 15.0,
            Action = "mute",
            RawScores = new Dictionary<string, double> { ["nudity"] = 0.80, ["immodesty"] = 0.10 }
        };

        Assert.True(segment.ShouldFilter(config));
        Assert.Equal("mute", segment.Action);
    }

    // ---------------------------------------------------------------
    // Sensitivity preset effects
    // ---------------------------------------------------------------

    [Fact]
    public void StrictPreset_CatchesLowerConfidenceContent()
    {
        var strictConfig = MakeConfig("strict");       // threshold = 0.45
        var permissiveConfig = MakeConfig("permissive"); // threshold = 0.85

        var segment = new Segment
        {
            Start = 0.0,
            End = 10.0,
            Action = "skip",
            RawScores = new Dictionary<string, double> { ["nudity"] = 0.60, ["immodesty"] = 0.10 }
        };

        Assert.True(segment.ShouldFilter(strictConfig), "strict should catch score=0.60");
        Assert.False(segment.ShouldFilter(permissiveConfig), "permissive should not catch score=0.60");
    }

    [Fact]
    public void DisabledCategory_DoesNotFilter()
    {
        var config = MakeConfig("strict", nudity: false, violence: false, profanity: false);
        // Only immodesty left — but set score for nudity which is disabled
        var segment = new Segment
        {
            Start = 0.0,
            End = 10.0,
            Action = "skip",
            RawScores = new Dictionary<string, double> { ["nudity"] = 0.99 }
        };

        Assert.False(segment.ShouldFilter(config));
    }

    [Fact]
    public void GetActiveCategories_ReturnsOnlyExceedingCategories()
    {
        var config = MakeConfig("moderate"); // thresholds: nsfw=0.65, violence=0.65
        var segment = new Segment
        {
            Start = 0.0,
            End = 10.0,
            Action = "skip",
            RawScores = new Dictionary<string, double>
            {
                ["nudity"] = 0.80,       // above threshold, immodesty confirmed → active
                ["immodesty"] = 0.10,    // confirms nudity detection
                ["violence"] = 0.50,     // below threshold → not active
            }
        };

        var categories = segment.GetActiveCategories(config);

        Assert.Contains("nudity", categories);
        Assert.DoesNotContain("violence", categories);
    }

    [Fact]
    public void MultipleCategories_AllExceedingThreshold_AllReturned()
    {
        var config = MakeConfig("moderate");
        var segment = new Segment
        {
            Start = 0.0,
            End = 10.0,
            Action = "skip",
            RawScores = new Dictionary<string, double>
            {
                ["nudity"] = 0.85,
                ["immodesty"] = 0.10,    // confirms nudity detection
                ["violence"] = 0.75
            }
        };

        var categories = segment.GetActiveCategories(config);

        Assert.Contains("nudity", categories);
        Assert.Contains("violence", categories);
    }
}
