using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Jellyfin.Plugin.ContentFilter.Models;
using Jellyfin.Plugin.ContentFilter.Services;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace Jellyfin.Plugin.ContentFilter.Tests;

public class SegmentStoreTests
{
    private static SegmentStore CreateStore() =>
        new SegmentStore(NullLogger<SegmentStore>.Instance);

    [Fact]
    public void Get_UnknownMediaId_ReturnsNull()
    {
        var store = CreateStore();

        var result = store.Get("nonexistent-media-id");

        Assert.Null(result);
    }

    [Fact]
    public void GetActiveSegments_UnknownMediaId_ReturnsEmptyList()
    {
        var store = CreateStore();

        var result = store.GetActiveSegments("nonexistent-media-id", 10.0);

        Assert.Empty(result);
    }

    [Fact]
    public void GetNextBoundary_UnknownMediaId_ReturnsNull()
    {
        var store = CreateStore();

        var result = store.GetNextBoundary("nonexistent-media-id", 0.0);

        Assert.Null(result);
    }

    [Fact]
    public async Task Put_ThenGet_ReturnsStoredData()
    {
        var store = CreateStore();
        const string mediaId = "test-media-1";
        var data = new SegmentData
        {
            MediaId = mediaId,
            Segments = new List<Segment>
            {
                new Segment { Start = 10.0, End = 20.0, Action = "skip" }
            }
        };

        // SaveToFile may fail if /segments is not writable in the test environment; that's expected.
        try { await store.Put(mediaId, data); }
        catch (Exception) { /* file I/O not required for in-memory test */ }

        var result = store.Get(mediaId);

        Assert.NotNull(result);
        Assert.Equal(mediaId, result.MediaId);
        Assert.Single(result.Segments);
    }

    [Fact]
    public async Task GetActiveSegments_AtMatchingPosition_ReturnsSegment()
    {
        var store = CreateStore();
        const string mediaId = "test-media-2";
        var data = new SegmentData
        {
            MediaId = mediaId,
            Segments = new List<Segment>
            {
                new Segment { Start = 30.0, End = 45.0, Action = "skip" },
                new Segment { Start = 90.0, End = 100.0, Action = "skip" }
            }
        };

        try { await store.Put(mediaId, data); }
        catch (Exception) { /* file I/O not required for in-memory test */ }

        var activeAt35 = store.GetActiveSegments(mediaId, 35.0);
        var activeAt50 = store.GetActiveSegments(mediaId, 50.0);

        Assert.Single(activeAt35);
        Assert.Equal(30.0, activeAt35[0].Start);
        Assert.Empty(activeAt50);
    }

    [Fact]
    public async Task GetNextBoundary_AfterCurrentPosition_ReturnsNextStart()
    {
        var store = CreateStore();
        const string mediaId = "test-media-3";
        var data = new SegmentData
        {
            MediaId = mediaId,
            Segments = new List<Segment>
            {
                new Segment { Start = 50.0, End = 60.0, Action = "skip" },
                new Segment { Start = 80.0, End = 90.0, Action = "skip" }
            }
        };

        try { await store.Put(mediaId, data); }
        catch (Exception) { /* file I/O not required for in-memory test */ }

        var nextFrom20 = store.GetNextBoundary(mediaId, 20.0);
        var nextFrom55 = store.GetNextBoundary(mediaId, 55.0);
        var nextFrom95 = store.GetNextBoundary(mediaId, 95.0);

        Assert.Equal(50.0, nextFrom20);
        Assert.Equal(80.0, nextFrom55);
        Assert.Null(nextFrom95);
    }

    [Fact]
    public async Task Put_OverwritesPreviousData()
    {
        var store = CreateStore();
        const string mediaId = "test-media-4";

        var data1 = new SegmentData
        {
            MediaId = mediaId,
            Segments = new List<Segment> { new Segment { Start = 1.0, End = 2.0 } }
        };
        var data2 = new SegmentData
        {
            MediaId = mediaId,
            Segments = new List<Segment>
            {
                new Segment { Start = 5.0, End = 10.0 },
                new Segment { Start = 15.0, End = 20.0 }
            }
        };

        try { await store.Put(mediaId, data1); } catch (Exception) { }
        try { await store.Put(mediaId, data2); } catch (Exception) { }

        var result = store.Get(mediaId);

        Assert.NotNull(result);
        Assert.Equal(2, result.Segments.Count);
        Assert.Equal(5.0, result.Segments[0].Start);
    }
}
