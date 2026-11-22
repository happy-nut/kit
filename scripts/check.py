import glob, json, os, re, subprocess, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root)
errors = []
PJ = '.claude-plugin/plugin.json'


def frontmatter(path):
    text = open(path).read()
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if not m:
        errors.append(f'{path}: frontmatter 없음')
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ':' in line and not line.startswith(' '):
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()
    return fm, text


def check_manifests_parse():
    for f in (PJ, '.claude-plugin/marketplace.json'):
        json.load(open(f))


def check_frontmatter(skills, agents):
    for name in skills:
        fm, _ = frontmatter(f'skills/{name}/SKILL.md')
        if fm.get('name') != name:
            errors.append(f'skills/{name}: name 이 폴더 이름과 다름')
        if fm.get('disable-model-invocation') != 'true':
            errors.append(f'skills/{name}: disable-model-invocation: true 아님')
        d = fm.get('description', '')
        if not d or len(d) >= 1024:
            errors.append(f'skills/{name}: description 없음 또는 너무 김')
        if re.search(r"Use (for|when)|'[A-Za-z][^']*'|\\\"[A-Za-z]", d):
            errors.append(f'skills/{name}: description 의 쓰는 때와 트리거 문구는 한국어로 쓴다(「…」에 쓴다). 영어 Use for 나 영어 인용 문구가 남았다')
    for name in agents:
        fm, _ = frontmatter(f'agents/{name}.md')
        if fm.get('name') != name or not fm.get('description'):
            errors.append(f'agents/{name}: name·description 확인')


def load_principles():
    path = 'skills/mode/principles.md'
    principles = set(re.findall(r'^## (.+?)\s*$', open(path).read(), re.M)) if os.path.exists(path) else set()
    if not principles:
        errors.append(f'{path}: 원칙 절(## 이름)이 없음')
    return principles


def check_references(skills, agents, principles):
    for path in glob.glob('skills/**/*.md', recursive=True) + glob.glob('agents/*.md') + glob.glob('docs/guide/*.md') + ['README.md', 'docs/authoring.md']:
        text = open(path).read()
        skill_dir = path.split('/')[1] if path.startswith('skills/') else None
        for s in re.findall(r'/dev:([a-z][\w-]*)', text):
            if s not in skills:
                errors.append(f'{path}: 없는 스킬 /dev:{s}')
        for a in re.findall(r'(?<![/\w])dev:([a-z][\w-]*)', text):
            if a not in agents and a not in skills:
                errors.append(f'{path}: 없는 에이전트 dev:{a}')
        for m in re.finditer(r'principles\.md 의 ', text):
            after = text[m.end():m.end() + 80]
            if not any(after.startswith(n) for n in principles):
                errors.append(f'{path}: principles.md 에 없는 원칙 「{after[:30]}」')
        if skill_dir:
            base = os.path.join('skills', skill_dir)
            for ref in re.findall(r'`?((?:\.\./[\w-]+/)?(?:playbooks|references|scripts)/[\w./-]+\.\w+)`?', text):
                target = os.path.normpath(os.path.join(base, ref))
                near = os.path.normpath(os.path.join(os.path.dirname(path), ref))
                if not any(os.path.exists(x) for x in (target, ref, near)):
                    errors.append(f'{path}: 없는 파일 {ref}')


def anchors(path):
    slugs = set()
    for title in re.findall(r'^#{1,6} (.+?)\s*$', open(path).read(), re.M):
        slugs.add(re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-'))
    return slugs


def check_guide_links():
    for path in glob.glob('docs/guide/*.md') + ['README.md']:
        for target, anchor in re.findall(r'\]\(<?([^)\s>#]*)(?:#([^)\s>]+))?>?(?:\s+"[^"]*")?\)', open(path).read()):
            if re.match(r'[a-z]+:', target):
                continue
            full = os.path.normpath(os.path.join(os.path.dirname(path), target)) if target else path
            if not os.path.exists(full):
                errors.append(f'{path}: 없는 링크 {target}')
            elif anchor and full.endswith('.md') and anchor not in anchors(full):
                errors.append(f'{path}: {target or path} 에 없는 제목 #{anchor}')


def check_readme(skills, principles):
    readme = open('README.md').read()
    counts = {'원칙': len(principles), '플레이북': len(glob.glob('skills/mode/playbooks/*.md'))}
    for word, n in counts.items():
        for m in re.finditer(rf'{word} (\d+)개', readme):
            if int(m.group(1)) != n:
                errors.append(f'README.md: 「{m.group(0)}」 인데 실제로는 {n}개다')
    for name in skills:
        if f'`/dev:{name}`' not in readme:
            errors.append(f'README.md: 스킬 표에 `/dev:{name}` 이 없다')


def private_words_from_user_config():
    cfg_path = os.path.expanduser('~/.claude/devkit.json')
    cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
    words = cfg.get('personal', {}).get('owners', []) + cfg.get('private_words', [])
    return re.compile('|'.join(words) if words else r'(?!)')


def check_no_private_words():
    private_words = private_words_from_user_config()
    origin = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip()
    slug = re.sub(r'^.*github\.com[:/]|\.git$', '', origin)
    publisher = slug.split('/')[0] if slug else ''
    tracked = subprocess.run(['git', 'ls-files', '-co', '--exclude-standard'], capture_output=True, text=True).stdout.splitlines()
    for path in tracked:
        if os.path.isfile(path) and b'\0' not in open(path, 'rb').read(8192):
            allowed = [slug, publisher] if path.startswith('.claude-plugin/') else [slug]
            for i, line in enumerate(open(path, errors='ignore').read().splitlines(), 1):
                for word in filter(None, allowed):
                    line = line.replace(word, '')
                if private_words.search(line):
                    errors.append(f'{path}:{i}: 특정 사람·앱·개인 도구 이름: {line.strip()[:80]}')


def check_author_email_is_noreply():
    email = subprocess.run(['git', 'config', 'user.email'], capture_output=True, text=True).stdout.strip()
    if email and not email.endswith('@users.noreply.github.com'):
        errors.append('git user.email 이 개인 메일이다. 이 저장소에선 GitHub noreply 메일을 쓴다: git config user.email <id>+<계정>@users.noreply.github.com')


def run_self_tests():
    for cmd in (['skills/no-comments/scripts/count.py', '--self-test'], ['skills/featuremap/scripts/featuremap.py', '--self-test'], ['.claude/skills/upstream/upstream.py', '--self-test'], ['scripts/shrink.py', '--self-test']):
        r = subprocess.run([sys.executable, '-I', *cmd], capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stdout + r.stderr)


skills = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob('skills/*/SKILL.md'))
agents = sorted(os.path.basename(p)[:-3] for p in glob.glob('agents/*.md'))
check_manifests_parse()
check_frontmatter(skills, agents)
principles = load_principles()
check_references(skills, agents, principles)
check_readme(skills, principles)
check_guide_links()
check_no_private_words()
check_author_email_is_noreply()
if errors:
    sys.exit('\n'.join(errors))
run_self_tests()
print(f'OK 스킬 {len(skills)} · 에이전트 {len(agents)} · 원칙 {len(principles)}')
