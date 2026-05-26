import re

APP_NAME = "EASY DEPLOY"
APP_VERSION = "2.2.5.27"
APP_DISPLAY_TITLE = f"{APP_NAME} v{APP_VERSION}"
LICENSE_HASH_ENV = "EASYDEPLOY_LICENSE_SHA256"
DEFAULT_LICENSE_SHA256 = "656427c46ba5939977ab0d94eef8f23087f30131514405ec8fb91f873db51b7a"
PAYLOAD_DIR_NAMES = ("EASY DEPLOY", "EASYDEPLOY")

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Z0-9-]{1,63}(?<!-)(\.(?!-)[A-Z0-9-]{1,63}(?<!-))*$",
    re.IGNORECASE,
)
NETBIOS_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,14}$", re.IGNORECASE)
HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Z0-9-]{1,63}(?<!-)(\.(?!-)[A-Z0-9-]{1,63}(?<!-))*$",
    re.IGNORECASE,
)
IPV4_RE = re.compile(r"^(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$")
PRODUCT_KEY_RE = re.compile(r"^[A-Z0-9]{5}(-[A-Z0-9]{5}){4}$", re.IGNORECASE)
