using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using Jellyfin.Plugin.ContentFilter.Configuration;

namespace Jellyfin.Plugin.ContentFilter.Services;

/// <summary>
/// Helpers for resolving configured scene-analyzer endpoints.
/// </summary>
public static class AiServiceEndpointHelper
{
    private static long _analysisCursor;

    /// <summary>
    /// Gets normalized, distinct AI service base URLs from plugin configuration.
    /// </summary>
    /// <param name="configuration">Plugin configuration.</param>
    /// <returns>List of normalized base URLs.</returns>
    public static IReadOnlyList<string> GetConfiguredBaseUrls(PluginConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(configuration);

        var tokens = new List<string>();
        if (!string.IsNullOrWhiteSpace(configuration.AiServiceBaseUrl))
        {
            tokens.Add(configuration.AiServiceBaseUrl);
        }

        if (!string.IsNullOrWhiteSpace(configuration.AiServiceBaseUrls))
        {
            var additional = configuration.AiServiceBaseUrls
                .Split(new[] { ',', ';', '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            tokens.AddRange(additional);
        }

        var results = new List<string>();
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var token in tokens)
        {
            if (!Uri.TryCreate(token, UriKind.Absolute, out var uri))
            {
                continue;
            }

            if (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps)
            {
                continue;
            }

            var normalized = uri.ToString().TrimEnd('/');
            if (seen.Add(normalized))
            {
                results.Add(normalized);
            }
        }

        return results;
    }

    /// <summary>
    /// Gets endpoints ordered for analysis requests according to load balancing mode.
    /// </summary>
    /// <param name="configuration">Plugin configuration.</param>
    /// <returns>Ordered endpoint list.</returns>
    public static IReadOnlyList<string> GetAnalysisOrder(PluginConfiguration configuration)
    {
        var endpoints = GetConfiguredBaseUrls(configuration);
        if (endpoints.Count <= 1)
        {
            return endpoints;
        }

        var mode = (configuration.AiServiceLoadBalancingMode ?? string.Empty).Trim().ToLowerInvariant();
        if (mode == "failover")
        {
            return endpoints;
        }

        var startIndex = (int)(Interlocked.Increment(ref _analysisCursor) % endpoints.Count);
        return Rotate(endpoints, startIndex);
    }

    private static IReadOnlyList<string> Rotate(IReadOnlyList<string> values, int startIndex)
    {
        if (values.Count == 0)
        {
            return values;
        }

        var rotated = new List<string>(values.Count);
        for (var i = 0; i < values.Count; i++)
        {
            rotated.Add(values[(startIndex + i) % values.Count]);
        }

        return rotated;
    }
}
