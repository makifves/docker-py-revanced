"""Check patching resource updates."""

from environs import Env
from loguru import logger

from main import get_app
from src.config import RevancedConfig
from src.manager.github import GitHubManager
from src.utils import default_build, integration_version_key, integrations_dl_key, patches_dl_key, patches_version_key


def check_if_build_is_required() -> bool:
    """Read resource version."""
    env = Env()
    env.read_env()
    config = RevancedConfig(env)
    needs_to_repatched = []

    for app_name in env.list("PATCH_APPS", default_build):
        logger.info(f"Checking {app_name}")
        app_obj = get_app(config, app_name)

        # Fetch old versions and sources
        old_integration_versions = GitHubManager(env).get_last_version(app_obj, integration_version_key)
        old_integration_sources = GitHubManager(env).get_last_version_source(app_obj, integrations_dl_key)
        old_patches_versions = GitHubManager(env).get_last_version(app_obj, patches_version_key)
        old_patches_sources = GitHubManager(env).get_last_version_source(app_obj, patches_dl_key)

        app_obj.download_patch_resources(config)

        # Fetch new versions and sources from app_obj's resources
        new_integration_versions = [res["version"] for res in app_obj.resource["integrations"]]
        new_integration_sources = [app_obj.integrations_dl]
        new_patches_versions = [res["version"] for res in app_obj.resource["patches"]]
        new_patches_sources = [app_obj.patches_dl]

        # Check if a new build is required by comparing each version and source
        should_trigger_integration_build = any(
            GitHubManager(env).should_trigger_build(
                old_version,
                old_source,
                new_version,
                new_source,
            )
            for old_version, old_source, new_version, new_source in zip(
                old_integration_versions,
                old_integration_sources,
                new_integration_versions,
                new_integration_sources,
                strict=False,
            )
        )

        should_trigger_patches_build = any(
            GitHubManager(env).should_trigger_build(
                old_version,
                old_source,
                new_version,
                new_source,
            )
            for old_version, old_source, new_version, new_source in zip(
                old_patches_versions,
                old_patches_sources,
                new_patches_versions,
                new_patches_sources,
                strict=False,
            )
        )

        if should_trigger_integration_build or should_trigger_patches_build:
            caused_by = {
                "app_name": app_name,
                "integration": {
                    "old": old_integration_versions,
                    "new": new_integration_versions,
                },
                "patches": {
                    "old": old_patches_versions,
                    "new": new_patches_versions,
                },
            }
            logger.info(f"New build can be triggered caused by {caused_by}")
            needs_to_repatched.append(app_name)

    logger.info(f"{needs_to_repatched} need to be repatched.")
    if needs_to_repatched:
        print(",".join(needs_to_repatched))  # noqa: T201
        return True

    return False


check_if_build_is_required()
