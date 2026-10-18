"""Build the separate Codex submission candidate without changing the base skill.

Standard library only. Does not install, execute tax tools, publish, or submit.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'distribution' / 'codex'
SKILL = 'skills/china-overseas-tax-skill/'


def package_files():
    files = {}

    def include(source, target):
        if source.is_symlink() or not source.is_file():
            raise ValueError('Missing or unexpected source: ' + str(source))
        files[target] = source.read_bytes()

    include(PROFILE / 'plugin.json', 'plugin.json')
    include(PROFILE / 'assets/icon.svg', 'assets/icon.svg')
    for name in ('PRIVACY.md', 'SUPPORT.md', 'TERMS.md'):
        include(PROFILE / name, name)
    include(ROOT / 'LICENSE', 'LICENSE')
    include(PROFILE / 'SKILL.md', SKILL + 'SKILL.md')
    include(ROOT / 'agents/openai.yaml', SKILL + 'agents/openai.yaml')
    for name in ('calculate.py', 'late_fees.py'):
        include(ROOT / 'scripts' / name, SKILL + 'scripts/' + name)
    for name in ('synthetic-ledger.json', 'synthetic-late-fees.json'):
        include(ROOT / 'examples' / name, SKILL + 'examples/' + name)
    for name in ('test_calculate.py', 'test_late_fees.py'):
        include(ROOT / 'tests' / name, SKILL + 'tests/' + name)
    for name in ('evidence.md', 'tax-rules.md', 'records.md',
                 'crs-reconciliation.md', 'dividend-credit.md', 'filing-and-late-fees.md', 'human-support.md'):
        include(ROOT / 'references' / name, SKILL + 'references/' + name)
    include(PROFILE / 'privacy-and-runtime.md', SKILL + 'references/privacy-and-runtime.md')

    # Preserve the shared document rules, replacing only the channel-specific footer.
    source = (ROOT / 'references/tax-authority-drafts.md').read_text(encoding='utf-8')
    before, sep, rest = source.partition('## 草稿回复末尾的固定提示')
    if not sep or '## 来源与金额边界' not in rest:
        raise ValueError('Draft reference changed: review profile transformation')
    _, _, after = rest.partition('## 来源与金额边界')
    replacement = '''## 草稿交付的一次使用提示

草稿正文、签名区及必要链接之后，在聊天回复中醒目提示一次：

**以上为参考草稿，请核对金额、资料来源及适用口径后再使用；正式申报以依法适用的要求和实际受理结果为准。**

提示不默认写入提交税局的正文，不替代必要事实和实际适用判断。人工支持入口按SKILL.md的阶段规则展示，客户未询问且不处于指定阶段时不附邮箱；需要展示则放在该提示之前，不进入文书正文。

## 来源与金额边界'''
    files[SKILL + 'references/tax-authority-drafts.md'] = (before + replacement + after).encode('utf-8')
    files['README.md'] = '''# 券商投资税务助手：官方提交候选包

版本1.0.0-rc.2，基于原版0.1.19共享的算术脚本及参考资料。

这是需要本地执行能力的skills-only插件包，不含MCP、hooks、遥测或作者服务器。按平台提供的本地插件安装流程使用；安装并不代表官方已审核或已上架。Python、PDF/Excel读取和OCR能力须由执行环境提供。

入口为skills/china-overseas-tax-skill/SKILL.md。PRIVACY.md和TERMS.md是待发布者确认的政策材料，SUPPORT.md提供实际支持邮箱。资料不自动发送给作者，不保证AI平台全程离线。

本候选只完成封装及静态结构检查。换环境运行、干净安装及扩展案例验证尚未开展；原版的历史测试结果不是本包端到端验证。正式提交还需处理可公开访问的政策材料、开发者身份/提交权限及真实运行验证，不因文件存在而视为已满足审核。
'''.encode('utf-8')
    manifest = json.loads(files['plugin.json'])
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
    files['PACKAGE-RECEIPT.json'] = json.dumps({
        'profile': 'codex-submission-candidate', 'version': manifest['version'],
        'base_version': '0.1.19', 'checks': 'packaging/static only',
        'runtime_validation': 'deferred by user', 'expanded_cases': 'deferred by user',
        'publication': 'not submitted or approved', 'sha256': hashes
    }, ensure_ascii=False, indent=2).encode('utf-8')
    validate(files)
    return files, manifest['version']


def validate(files):
    manifest = json.loads(files['plugin.json'])
    assert manifest['extensions']['com.openai']['requires_local_executor'] is True
    interface = manifest['extensions']['com.openai']['interface']
    for key in ('composerIcon', 'logo'):
        assert interface[key].startswith('./') and interface[key][2:] in files
    assert len(interface['displayName']) <= 30
    assert len(interface['shortDescription']) <= 30
    assert len(interface['longDescription']) <= 4000
    assert len(interface['defaultPrompt']) <= 3
    assert all(len(prompt) <= 128 for prompt in interface['defaultPrompt'])
    for name, data in files.items():
        parts = PurePosixPath(name).parts
        assert not name.startswith('/') and '..' not in parts
        assert not set(parts) & {'work', 'private', 'outputs', 'dist', '.git', '__pycache__'}
        if name.endswith(('.md', '.json', '.yaml', '.py', '.svg')):
            text = data.decode('utf-8')
            assert not re.search(r'[CD]:[/\\]|86189|17812395|U16567188', text), name
            assert not re.search(r'gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}', text), name
            if name.endswith('.md'):
                for link in re.findall(r'\]\(([^)]+)\)', text):
                    if '://' not in link and not link.startswith('#'):
                        target = str(PurePosixPath(name).parent / link.split('#')[0])
                        assert target in files, (name, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    files, version = package_files()
    destination = args.out or ROOT / 'dist' / ('china-overseas-tax-codex-' + version + '.zip')
    if destination.exists():
        raise FileExistsError('Inspect existing package before replacing: ' + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, 'w', compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = ZipInfo(name, date_time=(2026, 10, 18, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(files)
        assert all(archive.read(name) == data for name, data in files.items())
    print('Static package checks passed:', len(files), 'files;', destination.stat().st_size, 'bytes')
    print(destination)


if __name__ == '__main__':
    main()
