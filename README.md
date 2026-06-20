# ndaconstruct

Generate Non-Disclosure Agreements (NDAs) from the command line using an LLM
provider (OpenAI), with a free offline **mock** mode for testing.

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Offline mock mode (no API key, no network) — great for testing:
python -m src.main generate --count 10

# Real generation with OpenAI:
export OPENAI_API_KEY="sk-..."
python -m src.main generate --count 10 --provider openai --real
```

Generated NDAs are written to `./output/nda_001.txt`, `nda_002.txt`, ...

### Options

| Flag           | Description                                              | Default  |
| -------------- | -------------------------------------------------------- | -------- |
| `--count`      | Number of NDAs to generate                               | `1`      |
| `--provider`   | Provider to use with `--real` (`openai`, `mock`)         | `openai` |
| `--real`       | Call the real provider API (otherwise mock/offline)      | off      |
| `--output-dir` | Directory to write files into                            | `output` |
| `--seed`       | Random seed for reproducible NDA parameters              | none     |

### Environment variables

| Variable         | Description                                  | Default       |
| ---------------- | -------------------------------------------- | ------------- |
| `OPENAI_API_KEY` | OpenAI API key (required for `--real`)       | —             |
| `OPENAI_MODEL`   | Model to use                                 | `gpt-4o-mini` |

## How it works

- `--real` off → the `mock` provider renders a deterministic NDA template
  offline. No key or network needed.
- `--real` on → the selected provider (e.g. `openai`) calls the real API.

Each NDA is generated with randomized but plausible parameters (parties,
effective date, term, governing law, purpose).

> ⚠️ Generated documents are templates, **not legal advice**.

## Layout

```
src/
  main.py                  # CLI entry point (python -m src.main)
  generator.py             # generation loop -> files on disk
  models.py                # NDARequest data model + random sampling
  providers/
    base.py                # Provider interface
    mock.py                # offline templated provider
    openai_provider.py     # OpenAI-backed provider
```
