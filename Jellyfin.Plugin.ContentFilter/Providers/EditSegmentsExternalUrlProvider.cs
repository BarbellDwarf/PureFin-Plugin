using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Claims;
using Jellyfin.Database.Implementations.Enums;
using MediaBrowser.Controller.Entities;
using MediaBrowser.Controller.Entities.Movies;
using MediaBrowser.Controller.Library;
using MediaBrowser.Controller.Providers;
using Microsoft.AspNetCore.Http;

namespace Jellyfin.Plugin.ContentFilter.Providers;

/// <summary>
/// Provides an "Edit Segments" external link for movie detail pages.
/// </summary>
public sealed class EditSegmentsExternalUrlProvider : IExternalUrlProvider
{
    private readonly IHttpContextAccessor _httpContextAccessor;
    private readonly IUserManager _userManager;

    /// <summary>
    /// Initializes a new instance of the <see cref="EditSegmentsExternalUrlProvider"/> class.
    /// </summary>
    /// <param name="httpContextAccessor">HTTP context accessor.</param>
    /// <param name="userManager">User manager.</param>
    public EditSegmentsExternalUrlProvider(
        IHttpContextAccessor httpContextAccessor,
        IUserManager userManager)
    {
        _httpContextAccessor = httpContextAccessor;
        _userManager = userManager;
    }

    /// <inheritdoc />
    public string Name => "PureFin";

    /// <inheritdoc />
    public IEnumerable<string> GetExternalUrls(BaseItem item)
    {
        if (!IsCurrentRequestAdmin())
        {
            return Array.Empty<string>();
        }

        if (item is not Movie)
        {
            return Array.Empty<string>();
        }

        var itemId = item.Id;
        if (itemId == Guid.Empty)
        {
            return Array.Empty<string>();
        }

        return new[] { $"/Plugins/PureFin/Segments/Edit/{itemId:D}" };
    }

    private bool IsCurrentRequestAdmin()
    {
        var principal = _httpContextAccessor.HttpContext?.User;
        if (principal?.Identity?.IsAuthenticated != true)
        {
            return false;
        }

        var userIdClaimTypes = new[]
        {
            "Jellyfin-UserId",
            "UserId",
            ClaimTypes.NameIdentifier,
            "sub"
        };

        foreach (var claimType in userIdClaimTypes)
        {
            var claim = principal.Claims.FirstOrDefault(c => c.Type.Equals(claimType, StringComparison.OrdinalIgnoreCase));
            if (claim == null || !Guid.TryParse(claim.Value, out var userId))
            {
                continue;
            }

            var user = _userManager.GetUserById(userId);
            if (user != null && user.Permissions.Any(permission =>
                permission.Kind == PermissionKind.IsAdministrator && permission.Value))
            {
                return true;
            }
        }

        return principal.Claims.Any(claim =>
        {
            var isAdminClaimType =
                claim.Type.Contains("administrator", StringComparison.OrdinalIgnoreCase) ||
                claim.Type.Contains("admin", StringComparison.OrdinalIgnoreCase) ||
                claim.Type.EndsWith("role", StringComparison.OrdinalIgnoreCase);

            if (!isAdminClaimType)
            {
                return false;
            }

            return claim.Value.Equals("true", StringComparison.OrdinalIgnoreCase) ||
                   claim.Value.Contains("admin", StringComparison.OrdinalIgnoreCase);
        });
    }
}
