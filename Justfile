set shell := ["bash", "-euo", "pipefail", "-c"]

# Generate Markdown release notes for VERSION without modifying the repository.
release-notes version:
    #!/usr/bin/env bash
    set -euo pipefail

    version="{{ version }}"
    if git show-ref --verify --quiet "refs/tags/${version}"; then
        revision="${version}"
        previous="$(git describe --tags --abbrev=0 "${version}^")"
    else
        revision="HEAD"
        previous="$(git describe --tags --abbrev=0 HEAD)"
    fi

    uv run git-cliff "${previous}..${revision}" \
        --tag "${version}" \
        --config keepachangelog \
        --strip all

# Add generated notes to an existing GitHub release (requires the GitHub CLI).
publish-release-notes version:
    #!/usr/bin/env bash
    set -euo pipefail

    command -v gh >/dev/null || {
        echo "The GitHub CLI (gh) is required to publish release notes." >&2
        exit 1
    }

    notes_file="$(mktemp)"
    trap 'rm -f "${notes_file}"' EXIT
    uv run just release-notes "{{ version }}" > "${notes_file}"
    gh release edit "{{ version }}" --notes-file "${notes_file}"

# Bump VERSION_KIND (patch, minor, or major), commit, tag, and push the release.
release version_kind:
    #!/usr/bin/env bash
    set -euo pipefail

    version_kind="{{ version_kind }}"
    case "${version_kind}" in
        patch|minor|major) ;;
        *)
            echo "Version kind must be one of: patch, minor, major." >&2
            exit 2
            ;;
    esac

    if [[ "$(git branch --show-current)" != "main" ]]; then
        echo "Releases must be created from the main branch." >&2
        exit 1
    fi
    if [[ -n "$(git status --porcelain)" ]]; then
        echo "The working tree must be clean before creating a release." >&2
        exit 1
    fi

    git fetch origin main --tags
    if [[ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]]; then
        echo "Local main must match origin/main before creating a release." >&2
        exit 1
    fi

    uv run pytest
    uv run bumpver update "--${version_kind}" --ignore-vcs-tag --no-fetch
    version="$(uv run python -c 'from pytest_docker_compose import __version__; print(__version__)')"

    uv run just release-notes "${version}"
    git push origin main
    git push origin "${version}"

    echo
    echo "Release ${version} pushed. Once GitHub creates the release, publish its notes with:"
    echo "  uv run just publish-release-notes ${version}"
