from os import environ
from pathlib import Path
from typing import Any

import toml
from deepmerge import Merger
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


class WinstonConfigError(Exception):
    pass


def get_section(section: str) -> dict[str, Any]:
    """
    Load the section config from config-default.toml and config.toml.
    Use deepmerge.Merger to merge the configuration from config.toml
    and override that of config-default.toml.
    """
    # Load default configuration
    if not Path("config-default.toml").exists():
        raise WinstonConfigError("config-default.toml is missing")

    with open("config-default.toml", "r") as default_config_file:
        default_config = toml.load(default_config_file)

    # Load user configuration
    user_config = {}

    if Path("config.toml").exists():
        with open("config.toml", "r") as default_config_file:
            user_config = toml.load(default_config_file)

    # Merge the configuration
    merger = Merger([(dict, "merge")], ["override"], ["override"])

    conf = merger.merge(default_config, user_config)

    # Check whether we are missing the requested section
    if not conf.get(section):
        raise WinstonConfigError(f"Config is missing section '{section}'")

    return conf[section]


class ConfigSection(type):
    """Metaclass for loading TOML configuration into the relevant class."""

    def __new__(
        cls: type, name: str, bases: tuple[type], dictionary: dict[str, Any]
    ) -> type:
        """Use the section attr in the subclass to fill in the values from the TOML."""
        config = get_section(dictionary["section"])

        logger.info(f"Loading configuration section {dictionary['section']}")

        for key, value in config.items():
            if isinstance(value, dict):
                if env_var := value.get("env"):
                    if env_value := environ.get(env_var):
                        config[key] = env_value
                    else:
                        if not value.get("optional"):
                            raise WinstonConfigError(
                                f"Required config option '{key}' in"
                                f" '{dictionary['section']}' is missing, either set"
                                f" the environment variable {env_var} or override "
                                "it in your config.toml file"
                            )
                        else:
                            config[key] = None

        dictionary.update(config)

        config_section = super().__new__(cls, name, bases, dictionary)

        return config_section


class GeneralConfig(metaclass=ConfigSection):
    """General configuration for Winston."""

    section = "general"

    stream_url: str


class ZettaConfig(metaclass=ConfigSection):
    """Configuration for Zetta."""

    section = "zetta"

    host: str
    port: int

    silence_message: str


class AudioConfig(metaclass=ConfigSection):
    """Audio configuration for Winston."""

    section = "audio"

    ambient_db: float
    samples: int
    sample_dur: float
    threshold: float


class NotificationsConfig(metaclass=ConfigSection):
    """Configuration for Winston's notifications."""

    section = "notifications"

    discord: str
