import argparse
import logging
import sys

import httpx
import msgspec
from openpyxl import Workbook
from openpyxl.styles import Font
from statsuite_lib import NSIClient, KeycloakClient


from lib.models.simple_structure import Response

HEADERS = [
    "StructureType", "AgencyID", "StructureID", "Version", "IsFinal", "IsSemverFinal",
    "RefStructureType", "RefAgencyID", "RefStructureID", "RefVersion", "RefIsFinal", "RefIsSemverFinal",
]

violations = []
STRUCTURE_TYPES = ['agencyscheme', 'categorisation', 'categoryscheme', 'codelist', 'conceptscheme', 'contentconstraint', 'dataflow', 'datastructure', 'hierarchicalcodelist', 'metadatastructure']

log = logging.getLogger(__name__)

def main(base_url: str, output_file: str, keycloak_client: KeycloakClient | None = None):
    log.debug("Hello from sdmx3checker-nopysdmx!")

    client = NSIClient(base_url, keycloak_client=keycloak_client)

    for structure_type in STRUCTURE_TYPES:
        log.info(f'Checking {structure_type}')

        parsed_response = get_structures(client, f'{structure_type}?detail=allstubs')
        if parsed_response is None:
            continue
        for keys in parsed_response.data.keys():
            log.debug(keys)
            for item in parsed_response.data.get(keys):
                log.debug(item)
                if item.is_final or item.semver_is_final:
                    detail_parsed_response = get_structures(client, f'{structure_type}/{item.path}?detail=allstubs&references=all')
                    if detail_parsed_response is None:
                        continue
                    for ref_keys in detail_parsed_response.data.keys():
                        log.debug(ref_keys)
                        for ref_item in detail_parsed_response.data.get(ref_keys):
                            log.debug(ref_item)
                            if not (ref_item.is_final or ref_item.semver_is_final):
                                log.debug(f'Violation {structure_type} {item} references {ref_item}')
                                violations.append([
                                    keys, item.agency_id, item.id, item.version, item.is_final, item.semver_is_final,
                                    ref_keys, ref_item.agency_id, ref_item.id, ref_item.version, ref_item.is_final, ref_item.semver_is_final,
                                ])



    write_excel(output_file, HEADERS, violations)
    log.info(f'Wrote {len(violations)} violations to {output_file}')


def get_structures(client: NSIClient, path: str) -> Response | None:
    """GET a structure query and decode it; return None if the server answers 404."""
    try:
        log.debug(f'GET {client.NSI_URL}{path}')
        resp = client.get(path, headers={"Accept": "application/vnd.sdmx.structure+json"})
        log.debug(f'Response {resp.status_code} {resp.content.decode()}')

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            log.info(f'Not found (404), skipping: {path}')
            return None
        raise
    return msgspec.json.decode(resp.content, type=Response)


def write_excel(path: str, headers: list[str], rows: list[list]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = 'Violations'
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append(row)
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions
    for column in ws.columns:
        width = max(len(str(cell.value)) for cell in column)
        ws.column_dimensions[column[0].column_letter].width = width + 2
    wb.save(path)

                    
                

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check that final SDMX structures only reference final structures.")
    parser.add_argument("--base-url", required=True, help="NSI REST endpoint, e.g. https://nsi-address/rest/ or https://fmr-address/sdmx/v2/structure/")
    parser.add_argument("--output", required=True, help="Excel file to write, e.g. violations.xlsx")
    parser.add_argument("-d", "--debug", action="store_true", help="Show debug logging")
    parser.add_argument("--user", help="Keycloak username; requests are anonymous unless --user and --password are given")
    parser.add_argument("--password", help="Keycloak password")
    parser.add_argument("--openid-url", help="Keycloak OpenID configuration URL, required with --user/--password e.g. https://<keycloak-host>/realms/<realm>/.well-known/openid-configuration")
    args = parser.parse_args()
    if bool(args.user) != bool(args.password):
        parser.error("--user and --password must be given together")
    if args.user and not args.openid_url:
        parser.error("--openid-url is required with --user and --password")
    logging.basicConfig(stream=sys.stdout, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log.setLevel(logging.DEBUG if args.debug else logging.INFO)
    keycloak_client = None
    if args.user and args.password:
        keycloak_client = KeycloakClient(args.openid_url, args.user, args.password)
    # Request paths are appended to the base URL, so it must end with a slash
    main(args.base_url.rstrip("/") + "/", args.output, keycloak_client)
