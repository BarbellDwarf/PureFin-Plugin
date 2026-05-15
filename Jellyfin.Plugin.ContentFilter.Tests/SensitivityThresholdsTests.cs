using Jellyfin.Plugin.ContentFilter.Configuration;
using Xunit;

namespace Jellyfin.Plugin.ContentFilter.Tests;

public class SensitivityThresholdsTests
{
    [Theory]
    [InlineData("permissive", 0.85, 0.85)]
    [InlineData("moderate", 0.65, 0.65)]
    [InlineData("strict", 0.45, 0.45)]
    public void GetThresholds_ReturnsExpectedValues(string sensitivity, double expectedNsfw, double expectedViolence)
    {
        var (nsfwThreshold, violenceThreshold) = SensitivityThresholds.GetThresholds(sensitivity);

        Assert.Equal(expectedNsfw, nsfwThreshold, precision: 2);
        Assert.Equal(expectedViolence, violenceThreshold, precision: 2);
    }

    [Fact]
    public void UnknownSensitivity_ReturnsModeratDefault()
    {
        var (nsfwThreshold, violenceThreshold) = SensitivityThresholds.GetThresholds("unknown");

        Assert.Equal(0.65, nsfwThreshold, precision: 2);
        Assert.Equal(0.65, violenceThreshold, precision: 2);
    }

    [Fact]
    public void NullSensitivity_ReturnsModeratDefault()
    {
        var (nsfwThreshold, violenceThreshold) = SensitivityThresholds.GetThresholds(null);

        Assert.Equal(0.65, nsfwThreshold, precision: 2);
        Assert.Equal(0.65, violenceThreshold, precision: 2);
    }

    [Fact]
    public void StrictPreset_HasLowerThresholdThanPermissive()
    {
        var (strictNsfw, _) = SensitivityThresholds.GetThresholds("strict");
        var (permissiveNsfw, _) = SensitivityThresholds.GetThresholds("permissive");

        Assert.True(strictNsfw < permissiveNsfw, "Strict threshold should be lower than permissive");
    }

    [Fact]
    public void WithSensitivityThresholds_OverridesIndividualThresholds()
    {
        var config = new PluginConfiguration
        {
            Sensitivity = "strict",
            NudityThreshold = 0.99,
            ViolenceThreshold = 0.99
        };

        var effective = config.WithSensitivityThresholds();

        Assert.Equal(0.45, effective.NudityThreshold, precision: 2);
        Assert.Equal(0.45, effective.ViolenceThreshold, precision: 2);
    }

    [Fact]
    public void WithSensitivityThresholds_PreservesOtherSettings()
    {
        var config = new PluginConfiguration
        {
            Sensitivity = "moderate",
            EnableNudity = false,
            EnableViolence = true,
            AiServiceBaseUrl = "http://test:9999",
            ProfanityThreshold = 0.77
        };

        var effective = config.WithSensitivityThresholds();

        Assert.False(effective.EnableNudity);
        Assert.True(effective.EnableViolence);
        Assert.Equal("http://test:9999", effective.AiServiceBaseUrl);
        Assert.Equal(0.77, effective.ProfanityThreshold, precision: 2);
    }
}
