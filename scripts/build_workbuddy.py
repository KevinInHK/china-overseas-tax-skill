"""Build a WorkBuddy candidate from shared rules; no installation or submission."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def main():
    text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
    _, frontmatter, body = text.split('---', 2)
    description = re.search(r'^description: (.+)$', frontmatter, re.M).group(1)
    version = re.search(r'当前版本：\*\*([0-9.]+)\*\*',
                        (ROOT / 'README.md').read_text(encoding='utf-8')).group(1)
    metadata = {
        'name': 'china-overseas-tax-skill',
        'display_name': '券商投资税务助手',
        'display_name_en': 'Overseas Brokerage Tax Assistant',
        'description': description,
        'description_zh': '整理境外券商账单与历史成本，测算中国大陆税收居民的投资所得和参考税额，解释CRS差异及股息扣税。',
        'description_en': 'Review overseas brokerage statements and cost basis, estimate investment income and tax for Chinese mainland tax residents, and explain CRS differences and dividend withholding.',
        'version': version,
        'author': 'Kevin',
    }
    # JSON quoted strings are valid YAML scalars; do not disable automatic discovery.
    header = '\n'.join(k + ': ' + json.dumps(v, ensure_ascii=False)
                       for k, v in metadata.items())
    files = {'SKILL.md': ('---\n' + header + '\n---' + body).encode('utf-8')}
    for name in ['LICENSE', 'PRIVACY.md', 'SUPPORT.md', 'agents/openai.yaml']:
        files[name] = (ROOT / name).read_bytes()
    for name in ['calculate.py', 'late_fees.py']:
        files['scripts/' + name] = (ROOT / 'scripts' / name).read_bytes()
    for source in sorted((ROOT / 'references').glob('*.md')):
        if source.is_symlink():
            raise ValueError(source)
        files['references/' + source.name] = source.read_bytes()
    for name, data in files.items():
        assert not re.search(rb'gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{25,}|[CD]:[/\\]', data), name
        if name.endswith('.md'):
            for link in re.findall(r'\]\(([^)]+)\)', data.decode('utf-8')):
                if '://' in link or link.startswith(('#', 'mailto:')):
                    continue
                target = str(PurePosixPath(name).parent / link.split('#')[0])
                assert target in files, (name, target)
    files['PACKAGE-RECEIPT.json'] = json.dumps({
        'profile': 'workbuddy-candidate', 'version': version,
        'status': 'not installed, submitted or approved; category and support rules pending',
        'sha256': {n: hashlib.sha256(d).hexdigest() for n, d in sorted(files.items())},
    }, indent=2).encode('utf-8')
    output = ROOT / 'dist' / ('china-overseas-tax-workbuddy-' + version + '.zip')
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
        assert set(archive.namelist()) == {prefix + n for n in files}
        assert all(archive.read(prefix + n) == d for n, d in files.items())
    print('PASS: WorkBuddy metadata, links, ZIP content;', len(files), 'files')
    print(output)


if __name__ == '__main__':
    main()
