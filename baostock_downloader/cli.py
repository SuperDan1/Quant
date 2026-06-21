import sys
import click

from .downloader import DownloadManager
from .models import KlinePeriod
from .logger import setup_logger


@click.group()
@click.pass_context
def cli(ctx):
    """BaoStock 数据下载器 - 支持日/周/月/分钟线增量下载与校验。"""
    ctx.ensure_object(dict)


@cli.command()
@click.option("--code", "-c", help="股票代码，如 000001.SZ。不指定则下载全市场。")
@click.option("--cycle", "-y", type=click.Choice(["daily", "weekly", "monthly", "m5", "m15", "m30", "m60"]), help="K线周期。")
@click.option("--all-cycles", is_flag=True, help="下载所有周期（忽略 --cycle）。")
@click.option("--start", "-s", help="开始日期 YYYY-MM-DD。")
@click.option("--end", "-e", help="结束日期 YYYY-MM-DD。")
@click.pass_context
def download(ctx, code, cycle, all_cycles, start, end):
    """下载历史 K 线数据。"""
    log_dir = ctx.obj.get("log_dir", "logs")
    data_dir = ctx.obj.get("data_dir", "data")
    manifest_dir = ctx.obj.get("manifest_dir", "manifest")
    rate_limit = ctx.obj.get("rate_limit", 10)

    manager = DownloadManager(
        data_dir=data_dir,
        manifest_dir=manifest_dir,
        log_dir=log_dir,
        rate_limit=rate_limit,
    )

    period = KlinePeriod(cycle) if cycle else None

    try:
        result = manager.download(
            code=code,
            cycle=period,
            start_date=start,
            end_date=end,
            all_cycles=all_cycles,
        )
        click.echo(f"Done. success={result.success}, failed={result.failed}, skipped={result.skipped}")
        sys.exit(0 if result.failed == 0 else 1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--cycle", "-y", type=click.Choice(["daily", "weekly", "monthly", "m5", "m15", "m30", "m60"]), required=True, help="K线周期。")
@click.option("--all-cycles", is_flag=True, help="校验所有周期（忽略 --cycle）。")
@click.pass_context
def verify(ctx, cycle, all_cycles):
    """校验数据完整性并补漏。"""
    log_dir = ctx.obj.get("log_dir", "logs")
    data_dir = ctx.obj.get("data_dir", "data")
    manifest_dir = ctx.obj.get("manifest_dir", "manifest")
    rate_limit = ctx.obj.get("rate_limit", 10)

    manager = DownloadManager(
        data_dir=data_dir,
        manifest_dir=manifest_dir,
        log_dir=log_dir,
        rate_limit=rate_limit,
    )

    cycles = [KlinePeriod(cycle)]
    if all_cycles:
        cycles = list(KlinePeriod)

    for p in cycles:
        result = manager.verify_and_fix(p)
        click.echo(f"{p.value}: fixed={result['fixed']}, errors={len(result['errors'])}")
        for err in result["errors"]:
            click.echo(f"  ERROR: {err}", err=True)


cli.add_command(download)
cli.add_command(verify)


if __name__ == "__main__":
    cli(obj={})
