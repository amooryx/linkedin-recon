<div align="center">
  <img src="./banner.svg" alt="linkedin-recon" width="800">
</div>

# linkedin-recon

`linkedin-recon` creates narrowly scoped search links for **manual review** of
public professional sources. It does not contact search engines, scrape search
results or profile pages, collect names, or generate employee email guesses.
Search results are not verified by this tool.

Use it only for sources and targets you are authorized to research. Follow the
search provider's and source site's terms, applicable law, and any engagement
scope. Do not use it to bypass access controls or gather personal data at scale.

## Install

Requires Python 3.9 or newer. There are no runtime dependencies.

```bash
python -m pip install .
linkedin-recon --help
```

You can also run it directly from a checkout:

```bash
python linkedin_recon.py --help
```

## Usage

Generate a LinkedIn profile search link for a company and title:

```bash
linkedin-recon "Example Company" --title "Security Engineer"
```

Choose Bing and generate an additional job-posting query for technology terms:

```bash
linkedin-recon "Example Company" --title "Platform Engineer" --engine bing --tech
```

Save a machine-readable search plan:

```bash
linkedin-recon "Example Company" --tech --format json --out search-plan.json
```

The JSON schema includes `tool`, `schema_version`, the supplied `scope`, and
`searches`. Each search has a `type`, `engine`, encoded `url`, and human-readable
`query`. With `--out`, errors go to standard error and files are replaced
atomically; the output directory must already exist.

## Scope and limitations

- Supported search providers are Google and Bing. The tool only constructs
  links; opening a link and assessing any results are manual steps.
- The profile search uses the supplied company and title in a
  `site:linkedin.com/in` query. The optional technology search looks for terms
  in job postings. These are leads for review, not evidence that a person works
  at the company or that the company uses a technology.
- Company and title values are limited in length and cannot contain control
  characters. Do not put sensitive or personal information in the search
  scope.
- There is no network activity, search-result parsing, profile-page access,
  email-pattern generation, or implicit retry behavior.

## Development

Run the standard-library regression suite:

```bash
python -m unittest discover -s tests -v
```

**Omar Khalid** — [omareldemery.com](https://omareldemery.com)
