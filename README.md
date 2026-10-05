# sdmx3checker

Checks an SDMX registry for one SDMX 3.0 requirement: **a final structure must not depend on a structure that is not final.**

The script queries the registry's REST API and writes every structure that breaks this rule to an Excel file. It works with any registry that serves SDMX-JSON structure messages, including the .Stat Suite NSI web service and the Fusion Metadata Registry (FMR).

## What counts as final

A structure is final if either of these is true:

- **SDMX 2.1 style:** it has `isFinal: true`.
- **SDMX 3.0 style:** its version is a semantic version `MAJOR.MINOR.PATCH` with no pre-release suffix. For example, `1.0.0` and `2.3.1` are final, but `1.0.0-draft` is not. A two-part version such as `1.0` is not a semantic version, so it is final only if `isFinal` is true.

## How it works

1. For each structure type (agency schemes, categorisations, category schemes, codelists, concept schemes, content constraints, dataflows, data structures, hierarchical codelists and metadata structures), it lists all structures with `detail=allstubs`.
2. For each final structure, it fetches the structure again with `references=all` to get the structures related to it.
3. Each related structure that is not final is recorded as a violation.

If a request returns 404, for example because the registry doesn't support that structure type, the script logs it and moves on. Any other HTTP error stops the run.

**Limitation:** `references=all` returns both the structures this one depends on (children) and the structures that depend on it (parents). A non-final parent that uses a final structure doesn't break the rule, but the script currently reports it as a violation, so check the `RefStructureType` column when you review the results.

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/)

`uv run` installs the dependencies the first time you run the script.

## Usage

```
uv run python main.py --base-url <URL> --output <FILE.xlsx> [--user <USER> --password <PASSWORD> --openid-url <URL>] [-d]
```

| Option                 | Required      | Description                                                                                                           |
| ---------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------- |
| `--base-url`           | yes           | REST endpoint of the registry. A trailing `/` is added if missing.                                                    |
| `--output`             | yes           | Excel file to write. It is overwritten if it exists.                                                                  |
| `--user`, `--password` | no            | Keycloak credentials. Give both or neither. Without them, requests are anonymous.                                     |
| `--openid-url`         | with `--user` | Keycloak OpenID configuration URL, usually `https://<keycloak-host>/realms/<realm>/.well-known/openid-configuration`. |
| `-d`, `--debug`        | no            | Show debug logging, including every request and response.                                                             |

### Fusion Metadata Registry (anonymous)

```
uv run python main.py \
    --base-url 'https://fmr.example.org/sdmx/v2/structure' \
    --output fmr.xlsx
```

### .Stat Suite NSI (anonymous)

```
uv run python main.py \
    --base-url 'https://nsi.example.org/rest/' \
    --output nsi.xlsx
```

### .Stat Suite NSI (with Keycloak authentication)

```
uv run python main.py \
    --base-url 'https://nsi.example.org/rest/' \
    --output nsi.xlsx \
    --user '<user>' \
    --password '<password>' \
    --openid-url 'https://keycloak.example.org/realms/<realm>/.well-known/openid-configuration'
```

A password passed on the command line is saved in your shell history and is visible to other users of the machine while the script runs.

## Output

The Excel file has one sheet, `Violations`, with one row for each final structure and non-final related structure:

| Column                                                            | Description                                                                        |
| ----------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `StructureType`                                                   | Type of the final structure, as named in the SDMX-JSON response (e.g. `codelists`) |
| `AgencyID`, `StructureID`, `Version`                              | Identifies the final structure                                                     |
| `IsFinal`                                                         | The structure's `isFinal` value                                                    |
| `IsSemverFinal`                                                   | Whether the version is a semantic version with no pre-release suffix               |
| `RefStructureType`, `RefAgencyID`, `RefStructureID`, `RefVersion` | Identifies the related structure that is not final                                 |
| `RefIsFinal`, `RefIsSemverFinal`                                  | Same as above, for the related structure (both are false)                          |

The header row is bold and stays visible when you scroll, and filters are on.

## License

[MIT](LICENSE)
