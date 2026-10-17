"""Batch benchmark on synthetic PDFs only. Writes JSON with hardware, sizes, times and resources."""
import argparse
import json
import os
import platform
from pathlib import Path
import random
import shutil
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psutil
import core
from scripts.fixtures import make_pdf, KNOWN, UNKNOWN


def build_set(root: Path, count: int, seed: int = 7):
    """70 % known password, 10 % unknown, 10 % permissions-only, 10 % unencrypted; mixed sizes."""
    rnd = random.Random(seed)
    src = root / f'Source-{count}'
    if src.exists():
        shutil.rmtree(src)
    kinds = []
    for i in range(count):
        r = i % 10
        kind = 'unknown' if r == 0 else 'permissions' if r == 1 else 'plain' if r == 2 else 'known'
        pages = rnd.choice([1, 1, 2, 5, 20])
        pad = rnd.choice([0, 0, 20_000, 200_000])
        password = {'known': KNOWN, 'unknown': UNKNOWN, 'permissions': '', 'plain': None}[kind]
        make_pdf(src / f'folder-{i % 25:02d}' / f'doc-{i:05d}.pdf', password, pages=pages, text_bytes=pad)
        kinds.append(kind)
    sizes = [p.stat().st_size for p in src.rglob('*.pdf')]
    return src, kinds, sizes


def run(src: Path, dst: Path, qpdf: str, workers: int):
    if dst.exists():
        shutil.rmtree(dst)
    settings = core.Settings(src, dst, qpdf, [KNOWN], workers=workers, html_summary=True, app_version='benchmark')
    me = psutil.Process()
    peak = {'rss': me.memory_info().rss, 'children_rss': 0, 'samples': 0}
    done = threading.Event()

    def sample():
        while not done.is_set():
            try:
                peak['rss'] = max(peak['rss'], me.memory_info().rss)
                kids = me.children(recursive=True)
                peak['children_rss'] = max(peak['children_rss'], sum(k.memory_info().rss for k in kids if k.is_running()))
            except psutil.Error:
                pass
            peak['samples'] += 1
            time.sleep(0.05)
    sampler = threading.Thread(target=sample, daemon=True)
    cpu0 = psutil.cpu_times()
    t0 = time.perf_counter()
    sampler.start()
    results = {}
    core.process(settings, lambda k, p: results.update(p) if k == 'done' else None, threading.Event())
    elapsed = time.perf_counter() - t0
    done.set()
    sampler.join()
    cpu1 = psutil.cpu_times()
    busy = sum(getattr(cpu1, f) - getattr(cpu0, f) for f in ('user', 'system'))
    summary = results['summary']
    return {
        'workers': workers, 'elapsed_seconds': round(elapsed, 2),
        'pdfs_per_minute': round(summary['processed'] / elapsed * 60, 1),
        'status_counts': summary['status_counts'], 'totals': summary['totals'],
        'avg_cpu_percent_all_cores': round(100 * busy / (elapsed * (psutil.cpu_count() or 1)), 1),
        'peak_app_rss_mb': round(peak['rss'] / 1048576, 1),
        'peak_qpdf_children_rss_mb': round(peak['children_rss'] / 1048576, 1),
        'output_mb': round(sum(p.stat().st_size for p in dst.rglob('*.pdf')) / 1048576, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--qpdf', default=os.environ.get('RAR_TEST_QPDF') or shutil.which('qpdf'))
    ap.add_argument('--counts', default='100,1000')
    ap.add_argument('--workers', default='1,4')
    ap.add_argument('--root', default='qa/benchmark')
    ap.add_argument('--out', default='qa/benchmark.json')
    args = ap.parse_args()
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    vm = psutil.virtual_memory()
    report = {
        'machine': {'platform': platform.platform(), 'processor': platform.processor(),
                    'logical_cpus': psutil.cpu_count(), 'physical_cpus': psutil.cpu_count(logical=False),
                    'ram_gb': round(vm.total / 1073741824, 1), 'python': platform.python_version(),
                    'qpdf': core.qpdf_version(args.qpdf)},
        'data': 'Synthetic AES-256 PDFs: 70% known password, 10% unknown, 10% permissions-only, 10% unencrypted',
        'runs': [],
    }
    for count in map(int, args.counts.split(',')):
        t = time.perf_counter()
        src, kinds, sizes = build_set(root, count)
        info = {'pdfs': count, 'generation_seconds': round(time.perf_counter() - t, 1),
                'total_mb': round(sum(sizes) / 1048576, 2), 'min_kb': round(min(sizes) / 1024, 1),
                'max_kb': round(max(sizes) / 1024, 1), 'results': []}
        for w in map(int, args.workers.split(',')):
            r = run(src, root / f'Output-{count}-w{w}', args.qpdf, w)
            expected_unlocked = sum(k in ('known', 'permissions') for k in kinds)
            assert r['status_counts'].get('Unlocked', 0) == expected_unlocked, r
            assert r['status_counts'].get('PasswordNotMatched', 0) == kinds.count('unknown'), r
            info['results'].append(r)
            print(f"{count} PDFs, {w} worker(s): {r['elapsed_seconds']} s, {r['pdfs_per_minute']} PDFs/min")
        report['runs'].append(info)
        shutil.rmtree(src, ignore_errors=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
