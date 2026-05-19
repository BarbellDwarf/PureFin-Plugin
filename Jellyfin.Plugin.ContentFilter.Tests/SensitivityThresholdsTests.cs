using Jellyfin.Plugin.ContentFilter.Configuration;
using Xunit;

namespace Jellyfin.Plugin.ContentFilter.Tests;

public class SensitivityThresholdsTests
{
    [Theory]
    [InlineData("permissive", 0.75, 0.30, 0.80)]
    [InlineData("moderate",   0.50, 0.10, 0.70)]
    [InlineData("strict",     0.25, 0.05, 0.65)]
    public void GetThresholds_ReturnsExpectedValues(
        string sensitivity, double expectedNudity, double expectedImmodesty, double expectedViolence)
    {
        var (nudityThreshold, immodestyThreshold, violenceThreshold) = SensitivityThresholds.GetThresholds(sensitivity);

        Assert.Equal(expectedNudity,    nudityThreshold,    precision: 2);
        Assert.Equal(expectedImmodesty, immodestyThreshold, precision: 2);
        Assert.Equal(expectedViolence,  violenceThreshold,  precision: 2);
    }

    [Fact]
    public void UnknownSensitivity_ReturnsModeratDefault()
    {
        var (nudityThreshold, immodestyThreshold, violenceThreshold) = SensitivityThresholds.GetThresholds("unknown");

        Assert.Equal(0.50, nudityThreshold,    precision: 2);
        Assert.Equal(0.10, immodestyThreshold, precision: 2);
        Assert.Equal(0.70, violenceThreshold,  precision: 2);
    }

    [Fact]
    public void NullSensitivity_ReturnsModeratDefault()
    {
        var (nudityThreshold, immodestyThreshold, violenceThreshold) = SensitivityThresholds.GetThresholds(null);

        Assert.Equal(0.50, nudityThreshold,    precision: 2);
        Assert.Equal(0.10, immodestyThreshold, precision: 2);
        Assert.Equal(0.70, violenceThreshold,  precision: 2);
    }

    [Fact]
    public void StrictPreset_HasLowerThresholdThanPermissive()
    {
        var (strictNudity, strictImmodesty, _) = SensitivityThresholds.GetThresholds("strict");
        var (permissiveNudity, permissiveImmodesty, _) = SensitivityThresholds.GetThresholds("permissive");

        Assert.True(strictNudity    < permissiveNudity,    "Strict nudity threshold should be lower than permissive");
        Assert.True(strictImmodesty < permissiveImmodesty, "Strict immodesty threshold should be lower than permissive");
    }

    [Fact]
    public void ImmodestyThreshold_LowerThanNudityForAllPresets()
    {
        foreach (var preset in new[] { "strict", "moderate", "permissive" })
        {
            var (nudity, immodesty, _) = SensitivityThresholds.GetThresholds(preset);
            Assert.True(immodesty < nudity,
                $"Immodesty threshold ({immodesty}) should be lower than nudity threshold ({nudity}) for preset '{preset}'");
        }
    }

    [Fact]
    public void WithSensitivityThresholds_OverridesIndividualThresholds()
    {
        var config = new PluginConfiguration
        {
            Sensitivity = "strict",
            NudityThreshold = 0.99,
            ImmodestyThreshold = 0.99,
            ViolenceThreshold = 0.99
        };

        var effective = config.WithSensitivityThresholds();

        Assert.Equal(0.25, effective.NudityThreshold,    precision: 2);
        Assert.Equal(0.05, effective.ImmodestyThreshold, precision: 2);
        Assert.Equal(0.65, effective.ViolenceThreshold,  precision: 2);
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
