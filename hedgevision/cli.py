"""HedgeVision production CLI."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from hedgevision.broker import get_broker
from hedgevision.core.market_intel import run_market_intel
from hedgevision.mcp_server import run_mcp_server
from hedgevision.pipelines.daily_eod import run_daily_eod_sync

app = typer.Typer(help="HedgeVision production CLI")


def _choose(label: str, options: list[str]) -> str:
    typer.echo(f"\n{label}")
    for idx, opt in enumerate(options, start=1):
        typer.echo(f"  {idx}. {opt}")
    while True:
        choice = typer.prompt("Select option number")
        try:
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        except Exception:
            pass
        typer.secho("Invalid selection, try again.", fg=typer.colors.RED)


def _upsert_env_file(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    remaining = dict(values)
    out: list[str] = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in remaining:
                out.append(f"{key}={remaining.pop(key)}")
                continue
        out.append(line)
    if remaining:
        if out and out[-1].strip():
            out.append("")
        out.append("# Added by hedgevision-cli onboard")
        for key, value in remaining.items():
            out.append(f"{key}={value}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")


@app.command("sync")
def sync_pipeline(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate module resolution without executing the full pipeline.",
    )
) -> None:
    """Run daily EOD ingestion + analytics pipeline."""
    if dry_run:
        typer.echo("sync_dry_run_ok")
        return
    ok = run_daily_eod_sync()
    if not ok:
        raise typer.Exit(code=1)


@app.command("intel")
def market_intel(
    ticker: str = typer.Argument(..., help="Ticker symbol, e.g. BTC-USD"),
    news_url: str | None = typer.Option(None, "--url", help="Optional news URL for sentiment"),
    period: str = typer.Option("1y", "--period", help="History period"),
    use_llm: bool = typer.Option(False, "--use-llm", help="Use configured LLM provider"),
    provider: str | None = typer.Option(
        None, "--provider", help="LLM provider override: openai|anthropic|ollama"
    ),
    model: str | None = typer.Option(None, "--model", help="LLM model override"),
) -> None:
    """Run structured market intelligence verdict."""
    result = asyncio.run(
        run_market_intel(
            ticker=ticker,
            news_url=news_url,
            period=period,
            use_llm=use_llm,
            llm_provider=provider,
            llm_model=model,
        )
    )
    typer.echo(json.dumps(result, indent=2))


@app.command("broker-quote")
def broker_quote(
    symbol: str = typer.Argument(..., help="Symbol e.g. BTC-USD"),
    backend: str | None = typer.Option(
        None, "--backend", help="Broker backend override: paper|ccxt"
    ),
    exchange: str | None = typer.Option(
        None, "--exchange", help="CCXT exchange id (e.g. binance, kraken)"
    ),
) -> None:
    """Fetch a quote using local paper broker or optional CCXT adapter."""
    broker = get_broker(backend=backend, exchange=exchange)
    quote = broker.get_quote(symbol)
    typer.echo(json.dumps(quote.model_dump(), indent=2))


@app.command("mcp")
def mcp() -> None:
    """Run MCP server exposing HedgeVision quant tools."""
    run_mcp_server()


@app.command("onboard")
def onboard(
    env_file: str = typer.Option(
        "backend/api/.env",
        "--env-file",
        help="Path to backend env file to write onboarding values.",
    )
) -> None:
    """Interactive onboarding wizard for local-first setup."""
    typer.secho("HedgeVision Onboarding Wizard", fg=typer.colors.CYAN, bold=True)
    typer.echo("Step 1/5: data backend")
    data_backend = _choose("Choose data backend:", ["sqlite (recommended)", "supabase"])
    use_supabase = data_backend.startswith("supabase")

    typer.echo("Step 2/5: model runtime")
    provider = _choose(
        "Choose model runtime:",
        [
            "rules (fast local baseline)",
            "ollama (local LLM server)",
            "cpu (local CPU-bound quant model)",
            "openai (external)",
            "anthropic (external)",
        ],
    )
    provider_key = provider.split(" ", 1)[0]
    llm_model = "llama3.2"
    ollama_base = "http://localhost:11434"
    local_ml_backend = "numpy"
    local_ml_model_path = ""
    enable_external_llm = "false"

    if provider_key == "ollama":
        llm_model = typer.prompt("Ollama model", default="llama3.2")
        ollama_base = typer.prompt("Ollama base URL", default="http://localhost:11434")
    elif provider_key == "cpu":
        llm_model = typer.prompt("CPU local model name", default="cpu-linear-v1")
        local_ml_backend = _choose("CPU backend:", ["numpy", "sklearn", "onnx"])
        if local_ml_backend in {"sklearn", "onnx"}:
            local_ml_model_path = typer.prompt(
                "Local model path",
                default="./models/local_model.bin",
            )
    elif provider_key in {"openai", "anthropic"}:
        enable_external_llm = "true"
        llm_model = typer.prompt("Model name", default="gpt-4o-mini")

    typer.echo("Step 3/5: broker")
    broker = _choose("Choose broker backend:", ["paper (recommended)", "ccxt"])
    broker_key = broker.split(" ", 1)[0]
    ccxt_exchange = "binance"
    if broker_key == "ccxt":
        ccxt_exchange = typer.prompt("CCXT exchange id", default="binance")

    typer.echo("Step 4/5: optional services")
    enable_mcp = typer.confirm("Enable MCP server usage (local tool access)?", default=True)
    typer.echo("Step 5/5: write config")

    env_values = {
        "DATA_BACKEND": "supabase" if use_supabase else "sqlite",
        "DB_PATH": "backend/prices.db",
        "ENABLE_EXTERNAL_LLM": enable_external_llm,
        "LLM_PROVIDER": provider_key,
        "LLM_MODEL": llm_model,
        "OLLAMA_BASE_URL": ollama_base,
        "LOCAL_ML_BACKEND": local_ml_backend,
        "LOCAL_ML_MODEL_PATH": local_ml_model_path,
        "BROKER_BACKEND": broker_key,
        "CCXT_EXCHANGE": ccxt_exchange,
        "MODEL_VERSION": "prod-v1",
    }

    typer.echo("\nGenerated config:")
    for k, v in env_values.items():
        if v != "":
            typer.echo(f"{k}={v}")

    target = Path(env_file)
    if not target.is_absolute():
        target = (Path(__file__).resolve().parents[1] / target).resolve()
    if typer.confirm(f"Write these values to {target}?", default=True):
        _upsert_env_file(target, env_values)
        typer.secho(f"Saved onboarding config to {target}", fg=typer.colors.GREEN)
    else:
        typer.echo("No file written.")

    if enable_mcp:
        typer.echo("Next: run `hedgevision-cli mcp` when ready.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
