using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Jellyfin.Plugin.ContentFilter.Models;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.ContentFilter.Services;

/// <summary>
/// In-memory store for segment data with file system persistence.
/// </summary>
public class SegmentStore
{
    private readonly ConcurrentDictionary<string, SegmentData> _segments = new();
    private readonly ILogger<SegmentStore> _logger;
    private readonly string _segmentDirectory;

    /// <summary>
    /// Initializes a new instance of the <see cref="SegmentStore"/> class.
    /// </summary>
    /// <param name="logger">Logger instance.</param>
    public SegmentStore(ILogger<SegmentStore> logger)
    {
        _logger = logger;
        _segmentDirectory = Plugin.Instance?.Configuration.SegmentDirectory ?? "/segments";
    }

    /// <summary>
    /// Gets segment data for a media item.
    /// </summary>
    /// <param name="mediaId">Media item ID.</param>
    /// <returns>Segment data if found, null otherwise.</returns>
    public SegmentData? Get(string mediaId)
    {
        if (_segments.TryGetValue(mediaId, out var data))
        {
            return data;
        }

        // Try loading from file
        return LoadFromFile(mediaId);
    }

    /// <summary>
    /// Gets active segments at a specific timestamp.
    /// </summary>
    /// <param name="mediaId">Media item ID.</param>
    /// <param name="timestamp">Current playback timestamp in seconds.</param>
    /// <returns>List of active segments.</returns>
    public IReadOnlyList<Segment> GetActiveSegments(string mediaId, double timestamp)
    {
        var data = Get(mediaId);
        if (data == null)
        {
            return Array.Empty<Segment>();
        }

        return data.Segments
            .Where(s => s.Start <= timestamp && s.End >= timestamp)
            .ToList();
    }

    /// <summary>
    /// Gets the next segment boundary after a timestamp.
    /// </summary>
    /// <param name="mediaId">Media item ID.</param>
    /// <param name="timestamp">Current playback timestamp in seconds.</param>
    /// <returns>Next segment start time, or null if no upcoming segments.</returns>
    public double? GetNextBoundary(string mediaId, double timestamp)
    {
        var data = Get(mediaId);
        if (data == null)
        {
            return null;
        }

        return data.Segments
            .Where(s => s.Start > timestamp)
            .OrderBy(s => s.Start)
            .Select(s => (double?)s.Start)
            .FirstOrDefault();
    }

    /// <summary>
    /// Stores segment data for a media item.
    /// </summary>
    /// <param name="mediaId">Media item ID.</param>
    /// <param name="data">Segment data.</param>
    /// <returns>A <see cref="Task"/> representing the asynchronous operation.</returns>
    public async Task Put(string mediaId, SegmentData data)
    {
        _segments[mediaId] = data;
        await SaveToFile(mediaId, data);
    }

    /// <summary>
    /// Loads all segment files from the segment directory.
    /// </summary>
    /// <returns>A <see cref="Task"/> representing the asynchronous operation.</returns>
    public async Task LoadAll()
    {
        if (!Directory.Exists(_segmentDirectory))
        {
            _logger.LogInformation("Segment directory does not exist: {Directory}", _segmentDirectory);
            return;
        }

        var files = Directory.GetFiles(_segmentDirectory, "*.json", SearchOption.AllDirectories);
        _logger.LogInformation("Loading {Count} segment files from {Directory}", files.Length, _segmentDirectory);

        foreach (var file in files)
        {
            try
            {
                var json = await File.ReadAllTextAsync(file);
                var data = JsonSerializer.Deserialize<SegmentData>(json);
                if (data != null)
                {
                    _segments[data.MediaId] = data;
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error loading segment file: {File}", file);
            }
        }

        _logger.LogInformation("Loaded {Count} segment files", _segments.Count);
    }

    /// <summary>
    /// Reloads all segment data from disk. Useful when configuration changes or new segments are generated.
    /// </summary>
    /// <returns>Task representing the asynchronous operation.</returns>
    public async Task ReloadAll()
    {
        _logger.LogInformation("Reloading all segment data...");
        
        lock (_segments)
        {
            _segments.Clear();
        }
        
        await LoadAll();
        _logger.LogInformation("Segment data reloaded successfully");
    }

    private SegmentData? LoadFromFile(string mediaId)
    {
        var filePath = GetFilePath(mediaId);
        if (!File.Exists(filePath))
        {
            return null;
        }

        try
        {
            var json = File.ReadAllText(filePath);
            var data = JsonSerializer.Deserialize<SegmentData>(json);
            if (data != null)
            {
                _segments[mediaId] = data;
            }
            return data;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error loading segment file for media {MediaId}", mediaId);
            return null;
        }
    }

    private async Task SaveToFile(string mediaId, SegmentData data)
    {
        var filePath = GetFilePath(mediaId);
        var directory = Path.GetDirectoryName(filePath);
        
        if (directory != null && !Directory.Exists(directory))
        {
            Directory.CreateDirectory(directory);
        }

        try
        {
            var json = JsonSerializer.Serialize(data, new JsonSerializerOptions
            {
                WriteIndented = true
            });
            await File.WriteAllTextAsync(filePath, json);
            _logger.LogDebug("Saved segment file for media {MediaId}", mediaId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error saving segment file for media {MediaId}", mediaId);
        }
    }

    private string GetFilePath(string mediaId)
    {
        return Path.Combine(_segmentDirectory, $"{mediaId}.json");
    }
}
