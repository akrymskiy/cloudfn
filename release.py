#!/usr/bin/env python3
"""
Release script for the cloudfn package family.

Usage:
    python release.py <version>          # full release: branch + build + publish + merge
    python release.py <version> --dry-run  # build only, skip publish and git push

Publishes three packages in order:
    1. cloudfn-core
    2. cloudfn-aws  (depends on cloudfn-core==<version>)
    3. cloudfn      (meta, depends on both)

Requires:
    pip install build twine
    TWINE_USERNAME / TWINE_PASSWORD (or ~/.pypirc) set for PyPI auth.
"""

import argparse
import os
import shutil
import subprocess
import sys
import textwrap

REPO = os.path.dirname(os.path.abspath(__file__))
AUTHOR = "Aleksandr Krymskiy"
AUTHOR_EMAIL = "alex@krymskiy.net"
HOMEPAGE = "https://github.com/akrymskiy/cloudfn"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(*args, cwd=REPO, check=True, capture=False):
    kwargs = dict(cwd=cwd, check=check)
    if capture:
        kwargs.update(capture_output=True, text=True)
    return subprocess.run(args, **kwargs)


def current_branch():
    return run("git", "rev-parse", "--abbrev-ref", "HEAD", capture=True).stdout.strip()


def checkout(branch, create_from=None):
    if create_from:
        run("git", "checkout", "-b", branch, create_from)
    else:
        run("git", "checkout", branch)


def commit_all(message):
    run("git", "add", "-A")
    result = run("git", "status", "--porcelain", capture=True)
    if result.stdout.strip():
        run("git", "commit", "-m", message)
    else:
        print(f"  (no changes to commit for: {message})")


# ---------------------------------------------------------------------------
# pyproject.toml generators
# ---------------------------------------------------------------------------

def write_core_pyproject(version):
    content = textwrap.dedent(f"""\
        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"

        [project]
        name = "cloudfn-core"
        version = "{version}"
        description = "cloudfn-core"
        readme = "README.md"
        license = {{ text = "MIT" }}
        authors = [{{ name = "{AUTHOR}", email = "{AUTHOR_EMAIL}" }}]
        requires-python = ">=3.9"

        [project.scripts]
        cfn = "cloudfn.core.cli:main"

        [project.urls]
        Homepage = "{HOMEPAGE}"

        [tool.hatch.build.targets.wheel]
        packages = ["cloudfn/core"]
    """)
    path = os.path.join(REPO, "pyproject.toml")
    with open(path, "w") as f:
        f.write(content)


def write_aws_pyproject(version):
    content = textwrap.dedent(f"""\
        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"

        [project]
        name = "cloudfn-aws"
        version = "{version}"
        description = "cloudfn-aws"
        readme = "README.md"
        license = {{ text = "MIT" }}
        authors = [{{ name = "{AUTHOR}", email = "{AUTHOR_EMAIL}" }}]
        requires-python = ">=3.9"
        dependencies = [
            "cloudfn-core=={version}",
            "boto3",
        ]

        [project.urls]
        Homepage = "{HOMEPAGE}"

        [tool.hatch.build.targets.wheel]
        packages = ["cloudfn/aws"]
    """)
    path = os.path.join(REPO, "pyproject.toml")
    with open(path, "w") as f:
        f.write(content)


def write_meta_pyproject(version):
    content = textwrap.dedent(f"""\
        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"

        [project]
        name = "cloudfn"
        version = "{version}"
        description = "cloudfn"
        readme = "README.md"
        license = {{ text = "MIT" }}
        authors = [{{ name = "{AUTHOR}", email = "{AUTHOR_EMAIL}" }}]
        requires-python = ">=3.9"
        dependencies = [
            "cloudfn-core=={version}",
            "cloudfn-aws=={version}",
        ]

        [project.urls]
        Homepage = "{HOMEPAGE}"

        [tool.hatch.build.targets.wheel]
        packages = []
    """)
    path = os.path.join(REPO, "pyproject.toml")
    with open(path, "w") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Build & publish
# ---------------------------------------------------------------------------

def build(label):
    dist = os.path.join(REPO, "dist")
    if os.path.exists(dist):
        shutil.rmtree(dist)
    print(f"  building {label}...")
    run(sys.executable, "-m", "build", "--wheel", "--sdist")
    wheels = [f for f in os.listdir(dist) if f.endswith(".whl")]
    print(f"  built: {wheels}")


def publish():
    dist = os.path.join(REPO, "dist")
    print("  uploading to PyPI...")
    run(sys.executable, "-m", "twine", "upload", os.path.join(dist, "*"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Release cloudfn package family.")
    parser.add_argument("version", help="Version to release, e.g. 0.2.13")
    parser.add_argument("--dry-run", action="store_true",
                        help="Build but do not publish to PyPI or push branches.")
    args = parser.parse_args()

    version = args.version
    dry_run = args.dry_run

    # Ensure we start clean on master
    result = run("git", "status", "--porcelain", capture=True)
    if result.stdout.strip():
        print("ERROR: working tree is dirty. Commit or stash changes first.")
        sys.exit(1)

    origin = current_branch()
    if origin != "master":
        print(f"ERROR: must run from master (currently on '{origin}').")
        sys.exit(1)

    print(f"\n{'DRY RUN — ' if dry_run else ''}Releasing version {version}\n")

    # -----------------------------------------------------------------------
    # 1. cloudfn-core
    # -----------------------------------------------------------------------
    core_branch = f"release/cloudfn-core/{version}"
    print(f"[1/3] {core_branch}")
    checkout(core_branch, create_from="master")
    write_core_pyproject(version)
    commit_all(f"Release cloudfn-core=={version}")
    build("cloudfn-core")
    if not dry_run:
        publish()
        run("git", "push", "-u", "origin", core_branch)
    checkout("master")

    # -----------------------------------------------------------------------
    # 2. cloudfn-aws
    # -----------------------------------------------------------------------
    aws_branch = f"release/cloudfn-aws/{version}"
    print(f"\n[2/3] {aws_branch}")
    checkout(aws_branch, create_from="master")
    write_aws_pyproject(version)
    commit_all(f"Release cloudfn-aws=={version}")
    build("cloudfn-aws")
    if not dry_run:
        publish()
        run("git", "push", "-u", "origin", aws_branch)
    checkout("master")

    # -----------------------------------------------------------------------
    # 3. cloudfn (meta)
    # -----------------------------------------------------------------------
    meta_branch = f"release/cloudfn/{version}"
    print(f"\n[3/3] {meta_branch}")
    checkout(meta_branch, create_from="master")
    write_meta_pyproject(version)
    commit_all(f"Release cloudfn=={version}")
    build("cloudfn")
    if not dry_run:
        publish()
        run("git", "push", "-u", "origin", meta_branch)
    checkout("master")

    # -----------------------------------------------------------------------
    # 4. Merge source into master
    # -----------------------------------------------------------------------
    print("\n[4/4] Updating master")
    # Write all three pyproject variants would conflict — master holds the
    # meta pyproject.toml (the repo root package descriptor).
    write_meta_pyproject(version)
    commit_all(f"Release cloudfn=={version}")
    if not dry_run:
        run("git", "push", "origin", "master")

    print(f"\n{'DRY RUN complete' if dry_run else 'Release complete'}: cloudfn=={version} published.")
    if dry_run:
        print("Re-run without --dry-run to publish to PyPI and push branches.")


if __name__ == "__main__":
    main()
