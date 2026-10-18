"""Build a standard Skill ZIP from explicitly allowed public resources (stdlib only)."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def main():
    version = re.search(r'当前版本：\*\*([0-9.]+)\*\*',
                        (ROOT / 'README.md').read_text(encoding='utf-8')).group(1)
    names = ['SKILL.md', 'README.md', 'LICENSE', 'PRIVACY.md', 'SUPPORT.md',
             'llms.txt', 'agents/openai.yaml']
    for directory, suffix in [('references', '*.md'), ('examples', '*.json'),
                              ('tests', '*.py')]:
        names.extend(p.relative_to(ROOT).as_posix()
                     for p in sorted((ROOT / directory).glob(suffix)))
    names.extend('scripts/' + name for name in
                 ['calculate.py', 'late_fees.py', 'build_release.py'])
    files = {}
    for name in names:
        source = ROOT / name
        if source.is_symlink() or not source.is_file():
            raise ValueError('Missing or unexpected source: ' + name)
        files[name] = source.read_bytes()
    for name, data in files.items():
        if name.endswith('.md'):
            for link in re.findall(r'\]\(([^)]+)\)', data.decode('utf-8')):
                if '://' in link or link.startswith(('#', 'mailto:')):
                    continue
                target = str(PurePosixPath(name).parent / link.split('#')[0])
                # The standard README deliberately links to the separate source profile.
                if target.startswith('distribution/codex/'):
                    if not (ROOT / target).is_file():
                        raise ValueError(target)
                    continue
                if target not in files:
                    raise ValueError('Missing packaged reference: ' + target)
    # Point source-only profile documentation at GitHub in the standalone package.
    files['README.md'] = files['README.md'].replace(
        b'](distribution/codex/README.md)',
        b'](https://github.com/KevinInHK/china-overseas-tax-skill/blob/main/distribution/codex/README.md)')
    files['PACKAGE-RECEIPT.json'] = json.dumps({
        'version': version, 'profile': 'standard-skill',
        'checks': 'structure, links, ZIP integrity; no new runtime/case validation',
        'sha256': {k: hashlib.sha256(v).hexdigest() for k, v in sorted(files.items())}
    }, indent=2).encode('utf-8')
    output = ROOT / 'dist' / ('china-overseas-tax-skill-v' + version + '.zip')
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    prefix = 'china-overseas-tax-skill/'
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = ZipInfo(prefix + name, date_time=(2026, 10, 18, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {prefix + k for k in files}
        assert all(archive.read(prefix + k) == v for k, v in files.items())
    print('PASS: standard package, links, integrity;', len(files), 'files;',
          output.stat().st_size, 'bytes')
    print(output)


if __name__ == '__main__':
    main()
