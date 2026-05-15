#!/usr/bin/env python3
"""Generate/update Jellyfin plugin repository manifest."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

def load_build_yaml(path="build.yaml"):
    """Load plugin metadata from build.yaml."""
    import re
    with open(path) as f:
        content = f.read()
    
    def get_field(name):
        match = re.search(rf'^{name}:\s*["\']?([^"\'\n]+)["\']?', content, re.MULTILINE)
        return match.group(1).strip() if match else ""
    
    return {
        "guid": get_field("guid"),
        "name": get_field("name"),
        "description": get_field("description") or get_field("overview"),
        "overview": get_field("overview") or get_field("description"),
        "owner": get_field("owner"),
        "category": get_field("category"),
        "targetAbi": get_field("targetAbi"),
        "imageUrl": get_field("imageUrl"),
    }


def generate_manifest(version, tag, repo, output, build_yaml="build.yaml", checksum=""):
    meta = load_build_yaml(build_yaml)
    
    zip_name = f"{meta['name'].replace(' ', '_')}_{version}.zip"
    source_url = f"https://github.com/{repo}/releases/download/{tag}/{zip_name}"

    # If checksum not provided, try to read from a .md5 file beside the zip
    if not checksum:
        md5_path = f"{zip_name}.md5"
        if os.path.exists(md5_path):
            with open(md5_path) as f:
                checksum = f.read().strip()

    new_version_entry = {
        "version": version,
        "changelog": f"Release {tag}. See https://github.com/{repo}/releases/tag/{tag}",
        "targetAbi": meta.get("targetAbi", "10.9.0.0"),
        "sourceUrl": source_url,
        "checksum": checksum,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    
    # Load existing manifest or create new
    manifest = []
    if os.path.exists(output):
        with open(output) as f:
            try:
                manifest = json.load(f)
            except json.JSONDecodeError:
                manifest = []
    
    # Find or create plugin entry
    plugin_entry = None
    for entry in manifest:
        if entry.get("guid") == meta["guid"]:
            plugin_entry = entry
            break
    
    if plugin_entry is None:
        plugin_entry = {
            "guid": meta["guid"],
            "name": meta["name"],
            "description": meta.get("description", ""),
            "overview": meta.get("overview", ""),
            "owner": meta.get("owner", ""),
            "category": meta.get("category", "General"),
            "imageUrl": meta.get("imageUrl", ""),
            "versions": []
        }
        manifest.append(plugin_entry)
    
    # Prepend new version (newest first)
    versions = plugin_entry.get("versions", [])
    versions = [v for v in versions if v["version"] != version]  # remove existing same-version entry
    versions.insert(0, new_version_entry)
    plugin_entry["versions"] = versions
    
    os.makedirs(os.path.dirname(output) if os.path.dirname(output) else ".", exist_ok=True)
    with open(output, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Manifest written to {output}")
    print(f"Plugin: {meta['name']} v{version}")
    print(f"sourceUrl: {source_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--build-yaml", default="build.yaml")
    parser.add_argument("--checksum", default="")
    args = parser.parse_args()
    generate_manifest(args.version, args.tag, args.repo, args.output, args.build_yaml, args.checksum)
