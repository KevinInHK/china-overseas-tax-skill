"""Build a Tencent SkillHub candidate from public shared resources (stdlib only)."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def main():
    version = '0.1.25'
    summary = '分析境外券商账单，为中国大陆税收居民核算投资盈亏、股息及参考税额，支持预扣税抵免分析和CRS对账。'
    description = summary + ' 用户询问港美股报税、境外证券投资交税、FIFO历史成本、分红扣税或CRS差异时调用。支持申报参考说明；关键资料不足先补齐，不自动申报。'
    fields = {
        'name': 'china-overseas-tax-skill',
        'slug': 'china-overseas-tax-skill',
        'displayName': '境外券商投资税额测算',
        'version': version, 'summary': summary, 'description': description,
        'author': 'Kevin', 'license': 'MIT',
        'homepage': 'https://github.com/KevinInHK/china-overseas-tax-skill',
        'tags': ['tax', 'china', 'brokerage', 'capital-gains', 'dividends', 'crs'],
    }
    header = '\n'.join(k + ': ' + json.dumps(v, ensure_ascii=False) for k, v in fields.items())
    body = (ROOT / 'SKILL.md').read_text(encoding='utf-8').split('---', 2)[2]
    body = body.replace('# 券商投资税务助手', '# 境外券商投资税额测算', 1)
    files = {'SKILL.md': ('---\n' + header + '\n---' + body).encode('utf-8')}
    for name in ['LICENSE', 'PRIVACY.md', 'SUPPORT.md', 'agents/openai.yaml']:
        text = (ROOT / name).read_text(encoding='utf-8')
        if name == 'PRIVACY.md':
            text = text.replace('普通版Skill。', '普通版Skill及同源SkillHub版（展示名“境外券商投资税额测算”）。')
        if name == 'agents/openai.yaml':
            text = text.replace('券商投资税务助手', '境外券商投资税额测算')
        files[name] = text.encode('utf-8')
    for name in ['calculate.py', 'late_fees.py']:
        files['scripts/' + name] = (ROOT / 'scripts' / name).read_bytes()
    for p in sorted((ROOT / 'references').glob('*.md')):
        if p.is_symlink():
            raise ValueError(p)
        files['references/' + p.name] = p.read_bytes()
    files['PACKAGE-RECEIPT.json'] = json.dumps({
        'profile': 'tencent-skillhub-candidate', 'version': version,
        'status': 'prepared; not submitted or approved',
        'sha256': {n: hashlib.sha256(d).hexdigest() for n, d in sorted(files.items())},
    }, indent=2).encode('utf-8')
    output = ROOT / 'dist' / ('china-overseas-tax-skillhub-' + version + '.zip')
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'w', ZIP_DEFLATED) as z:
        for name, data in sorted(files.items()):
            info = ZipInfo('china-overseas-tax-skill/' + name, date_time=(2026, 10, 18, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    with ZipFile(output) as z:
        assert z.testzip() is None
        assert all(z.read('china-overseas-tax-skill/' + n) == d for n, d in files.items())
    print(output)


if __name__ == '__main__':
    main()
