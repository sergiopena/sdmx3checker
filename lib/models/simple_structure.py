from importlib.metadata import version
import h11._version
import re
from httpx import __version__
import msgspec

_SEMVER_PATTERN = re.compile(
    r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)

class Structure(msgspec.Struct, frozen=True):
    id: str
    agency_id: str = msgspec.field(name="agencyID")
    version: str
    is_final: bool = msgspec.field(name="isFinal")

    @property
    def path(self) -> str:
        return f'{self.agency_id}/{self.id}/{self.version}'

    def add_violation(self, message: str) -> None:
        self.violations.append(message)

    @property
    def is_valid(self) -> bool:
        return not self.violations

    @property
    def is_semver(self) -> bool:
        return bool(_SEMVER_PATTERN.match(self.version))

    @property
    def semver_is_final(self) -> bool:
        return self.is_semver and "-" not in self.version



# Every key under "data" (e.g. "metadataStructures", "conceptSchemes"), mapped to its items
ResponseData = dict[str, list[Structure]]


class Response(msgspec.Struct, frozen=True):
    data: ResponseData
