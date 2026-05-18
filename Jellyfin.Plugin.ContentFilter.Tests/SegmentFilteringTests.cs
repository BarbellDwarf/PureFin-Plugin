using System.Collections.Generic;
using Jellyfin.Plugin.ContentFilter.Configuration;
using Jellyfin.Plugin.ContentFilter.Models;
using Xunit;

namespace Jellyfin.Plugin.ContentFilter.Tests;

/// <summary>
/// Tests for Segment.ShouldFilter() with the nudity confirmation composite gate.
/// </summary>
public class SegmentFilteringTests
{
    private static PluginConfiguration DefaultConfig(double nudityConfirmMin = 0.05) => new()
    {
        EnableNudity = true,
        EnableImmodesty = true,
        EnableViolence = true,
        NudityThreshold = 0.30,
        ImmodestyThreshold = 0.12,
        ViolenceThreshold = 0.40,
        NudityConfirmationMinImmodesty = nudityConfirmMin
    };

    [Fact]
    public void ShouldFilter_FalsePositive_HighNudityNearZeroImmodesty_ReturnsFalse()
    {
        // Hostiles false-positive pattern: NSFW model fires on skin-toned backgrounds
        // but immodesty classifier correctly identifies no immodest content.
        var segment = new Segment
        {
            Start = 375.7, End = 401.2,
            RawScores = new Dictionary<string, double>
            {
                { "nudity", 0.965 },
                { "immodesty", 0.0 },
                { "violence", 0.0 }
            }
        };

        var result = segment.ShouldFilter(DefaultConfig(nudityConfirmMin: 0.05));

        Assert.False(result, "High nudity + near-zero immodesty should be rejected as false positive");
    }

    [Fact]
    public void ShouldFilter_RealContent_HighNudityAndImmodesty_ReturnsTrue()
    {
        // 2F2F bikini/swimwear: both models agree
        var segment = new Segment
        {
            Start = 74.1, End = 80.2,
            RawScores = new Dictionary<string, double>
            {
                { "nudity", 0.985 },
                { "immodesty", 0.15 },
                { "violence", 0.0 }
            }
        };

        var result = segment.ShouldFilter(DefaultConfig(nudityConfirmMin: 0.05));

        Assert.True(result, "High nudity + above-minimum immodesty should be filtered");
    }

    [Fact]
    public void ShouldFilter_ConfirmationDisabled_HighNudityAloneSufficient()
    {
        // When NudityConfirmationMinImmodesty = 0.0, confirmation is off
        var segment = new Segment
        {
            Start = 0, End = 5,
            RawScores = new Dictionary<string, double>
            {
                { "nudity", 0.90 },
                { "immodesty", 0.001 },
                { "violence", 0.0 }
            }
        };

        var result = segment.ShouldFilter(DefaultConfig(nudityConfirmMin: 0.0));

        Assert.True(result, "With confirmation disabled, nudity alone should trigger filter");
    }

    [Fact]
    public void ShouldFilter_ImmodestyAlone_ExceedsThreshold_ReturnsTrue()
    {
        // Immodesty category is independent of nudity confirmation gate
        var segment = new Segment
        {
            Start = 0, End = 5,
            RawScores = new Dictionary<string, double>
            {
                { "nudity", 0.05 },
                { "immodesty", 0.50 },
                { "violence", 0.0 }
            }
        };

        var result = segment.ShouldFilter(DefaultConfig());

        Assert.True(result, "Immodesty alone exceeding threshold should trigger filter regardless of nudity");
    }

    [Fact]
    public void ShouldFilter_NudityJustAtConfirmMinimum_ReturnsTrue()
    {
        // Immodesty exactly at the confirmation minimum is sufficient to confirm
        var segment = new Segment
        {
            Start = 0, End = 5,
            RawScores = new Dictionary<string, double>
            {
                { "nudity", 0.80 },
                { "immodesty", 0.05 },
                { "violence", 0.0 }
            }
        };

        var result = segment.ShouldFilter(DefaultConfig(nudityConfirmMin: 0.05));

        Assert.True(result, "Immodesty at exactly the confirmation minimum should confirm nudity detection");
    }

    [Fact]
    public void GetActiveCategories_FalsePositive_ExcludesNudity()
    {
        var segment = new Segment
        {
            Start = 0, End = 5,
            RawScores = new Dictionary<string, double>
            {
                { "nudity", 0.965 },
                { "immodesty", 0.0 },
                { "violence", 0.0 }
            }
        };

        var categories = segment.GetActiveCategories(DefaultConfig(nudityConfirmMin: 0.05));

        Assert.DoesNotContain("nudity", categories);
    }

    [Fact]
    public void GetActiveCategories_RealContent_IncludesNudity()
    {
        var segment = new Segment
        {
            Start = 0, End = 5,
            RawScores = new Dictionary<string, double>
            {
                { "nudity", 0.90 },
                { "immodesty", 0.10 },
                { "violence", 0.0 }
            }
        };

        var categories = segment.GetActiveCategories(DefaultConfig(nudityConfirmMin: 0.05));

        Assert.Contains("nudity", categories);
    }

    [Fact]
    public void ShouldFilter_AllDisabled_ReturnsFalse()
    {
        var config = new PluginConfiguration
        {
            EnableNudity = false,
            EnableImmodesty = false,
            EnableViolence = false,
            EnableProfanity = false
        };
        var segment = new Segment
        {
            Start = 0, End = 5,
            RawScores = new Dictionary<string, double>
            {
                { "nudity", 1.0 },
                { "immodesty", 1.0 },
                { "violence", 1.0 }
            }
        };

        Assert.False(segment.ShouldFilter(config));
    }
}
