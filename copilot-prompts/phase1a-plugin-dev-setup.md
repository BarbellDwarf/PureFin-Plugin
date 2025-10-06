# Phase 1A: Plugin Development Environment Setup

## Overview
Set up the development environment for creating a custom Jellyfin plugin, including .NET development tools, Jellyfin plugin template, and basic project structure.

## Prerequisites
- Windows 10/11, macOS, or Linux development machine
- Minimum 8GB RAM, 16GB recommended
- 20GB free disk space
- Administrative/sudo access for software installation

## Tasks

### Task 1: Install Development Tools
**Duration**: 1-2 hours
**Priority**: Critical

#### Subtasks:
1. **Install .NET SDK**
   ```bash
   # Download and install .NET 6.0 SDK or higher
   # Windows: Download from Microsoft official site
   # macOS: brew install dotnet
   # Linux: Follow distribution-specific instructions
   ```

2. **Install Visual Studio or VS Code**
   - Visual Studio 2022 Community (Windows/Mac) - Recommended
   - OR Visual Studio Code with C# extension (Cross-platform)

3. **Install Docker Desktop**
   - Download from docker.com
   - Required for AI service containerization
   - Verify installation: `docker --version`

4. **Install Git**
   - Required for version control and cloning templates
   - Configure with your credentials

#### Acceptance Criteria:
- [ ] `dotnet --version` returns 6.0 or higher
- [ ] IDE successfully opens and compiles C# projects
- [ ] Docker Desktop runs and can pull images
- [ ] Git is configured with user credentials

### Task 2: Clone and Setup Jellyfin Plugin Template
**Duration**: 30 minutes
**Priority**: Critical

#### Subtasks:
1. **Clone Plugin Template**
   ```bash
   git clone https://github.com/jellyfin/jellyfin-plugin-template.git
   cd jellyfin-plugin-template
   ```

2. **Customize Template for Content Filter Plugin**
   - Rename project directory to `Jellyfin.Plugin.ContentFilter`
   - Update `Jellyfin.Plugin.ContentFilter.csproj` with new name
   - Modify namespace and class names in template files

3. **Update Plugin Manifest**
   - Edit `build.yaml` with plugin metadata
   - Set unique GUID for the plugin
   - Define version and compatibility information

4. **Initial Build Test**
   ```bash
   dotnet build
   dotnet pack --configuration Release
   ```

#### Files to Modify:
- `Jellyfin.Plugin.ContentFilter.csproj`
- `Plugin.cs` - Main plugin class
- `Configuration/PluginConfiguration.cs`
- `build.yaml`

#### Acceptance Criteria:
- [ ] Project builds without errors
- [ ] Plugin manifest contains correct metadata
- [ ] Generated DLL has appropriate naming
- [ ] Template structure is ready for customization

### Task 3: Setup Local Jellyfin Test Environment
**Duration**: 1-2 hours
**Priority**: High

#### Subtasks:
1. **Install Jellyfin Server Locally**
   ```bash
   # Using Docker (Recommended)
   docker run -d --name jellyfin-test \
     -p 8096:8096 \
     -v jellyfin-config:/config \
     -v jellyfin-cache:/cache \
     -v /path/to/media:/media \
     jellyfin/jellyfin:latest
   ```

2. **Complete Jellyfin Initial Setup**
   - Access http://localhost:8096
   - Complete setup wizard
   - Create admin user
   - Add test media library

3. **Install Plugin Development Tools**
   - Enable developer mode in Jellyfin settings
   - Configure plugin directories
   - Set up hot-reload for development

#### Acceptance Criteria:
- [ ] Jellyfin web interface accessible at localhost:8096
- [ ] Test media library configured and scanning
- [ ] Plugin directory writable and accessible
- [ ] Development mode enabled

### Task 4: Development Workflow Setup
**Duration**: 1 hour
**Priority**: Medium

#### Subtasks:
1. **Configure Build Scripts**
   ```bash
   # Create build script for plugin deployment
   #!/bin/bash
   dotnet build --configuration Debug
   cp bin/Debug/net6.0/Jellyfin.Plugin.ContentFilter.dll /path/to/jellyfin/plugins/
   ```

2. **Setup Debug Configuration**
   - Configure IDE for Jellyfin plugin debugging
   - Set breakpoints and logging
   - Test debug attachment to Jellyfin process

3. **Version Control Setup**
   - Initialize Git repository for plugin
   - Create .gitignore for .NET projects
   - Set up branching strategy (main, develop, feature branches)

4. **Documentation Structure**
   ```
   docs/
   ├── api-reference.md
   ├── configuration.md
   └── development-guide.md
   ```

#### Acceptance Criteria:
- [ ] Build script successfully deploys plugin to Jellyfin
- [ ] Debugger can attach and hit breakpoints
- [ ] Git repository initialized with proper .gitignore
- [ ] Documentation structure created

## Deliverables

### Code Deliverables:
1. **Jellyfin.Plugin.ContentFilter** - Base plugin project
2. **Build Scripts** - Automated build and deployment
3. **Configuration Classes** - Plugin settings structure
4. **Unit Test Project** - Basic testing framework

### Documentation Deliverables:
1. **Development Environment Guide** - Setup instructions
2. **Plugin Architecture Document** - Technical overview
3. **Build and Deployment Guide** - CI/CD processes

## Verification Steps

### Manual Testing:
1. Build plugin from source without errors
2. Deploy plugin to local Jellyfin instance
3. Verify plugin appears in Jellyfin admin dashboard
4. Confirm plugin configuration page loads

### Automated Testing:
1. Unit tests run successfully
2. Build scripts complete without errors
3. Plugin manifest validation passes

## Troubleshooting

### Common Issues:
1. **Build Errors**
   - Verify .NET SDK version compatibility
   - Check NuGet package references
   - Ensure all dependencies are restored

2. **Plugin Not Loading**
   - Verify DLL is in correct plugins directory
   - Check Jellyfin logs for loading errors
   - Ensure plugin manifest is valid

3. **Docker Issues**
   - Verify Docker Desktop is running
   - Check port conflicts (8096)
   - Ensure volume mounts are correct

## Next Phase Dependencies

This phase must be completed before proceeding to:
- Phase 1B: AI Service Infrastructure
- Phase 2A: AI Model Integration
- Phase 3A: Plugin Core Development

## Success Metrics
- [ ] Development environment fully functional
- [ ] Plugin template successfully customized
- [ ] Local Jellyfin test environment operational
- [ ] Build and deployment pipeline established
- [ ] All acceptance criteria met

## Resources
- [Jellyfin Plugin Development Docs](https://jellyfin.org/docs/general/server/plugins/)
- [.NET 6.0 Documentation](https://docs.microsoft.com/en-us/dotnet/)
- [Docker Desktop Documentation](https://docs.docker.com/desktop/)