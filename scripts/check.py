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


def check_old_names_and_references(skills, agents, principles):
    forbidden = re.compile(r'pstack|poteto|[Cc]ursor|AskQuestion|[Gg]emini|—')
    for path in glob.glob('skills/**/*', recursive=True) + glob.glob('agents/*.md'):
        if not os.path.isfile(path) or not path.endswith(('.md', '.sh', '.mjs', '.ts', '.py')):
            continue
        text = open(path).read()
        for i, line in enumerate(text.splitlines(), 1):
            if forbidden.search(line) and not ('.test.' in path and '—' in line and not re.search(r'pstack|poteto|[Cc]ursor|AskQuestion|[Gg]emini', line)):
                errors.append(f'{path}:{i}: 옮기기 전 흔적 또는 긴 대시: {line.strip()[:80]}')
        if not path.endswith('.md'):
            continue
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


def check_required_sentences():
    required = {
        'skills/mode/SKILL.md': ['## 신뢰 피라미드', '사용자에게 교정을 받음'],
        'skills/mode/playbooks/autonomous-run.md': ['0. 돌리기 전에 이 저장소가 믿을 만한지 본다.'],
        'skills/correct/SKILL.md': ['교정할 때마다'],
    }
    for f, needles in required.items():
        body = open(f).read() if os.path.exists(f) else ''
        for n in needles:
            if n not in body:
                errors.append(f'{f}: 빠지면 안 되는 문장 「{n}」 이 없음')
    for path in glob.glob('skills/**/*.md', recursive=True):
        for i, line in enumerate(open(path).read().splitlines(), 1):
            if re.search(r'두 번[^.]{0,12}(지적|고치|교정)|(지적|교정)[^.]{0,12}두 번(?!째를 기다리지)', line):
                errors.append(f'{path}:{i}: 교정은 매번 굳힌다. 「두 번」 조건이 남음')


def check_single_source(principles):
    hooks = sorted({h['command'].split('/')[-1] for g in json.load(open('hooks/hooks.json'))['hooks'].values() for e in g for h in e['hooks']})
    readme = open('README.md').read()
    listed = sorted(set(re.findall(r'^\| `hooks/([\w-]+\.py)`', readme, re.M)))
    if listed != hooks:
        errors.append(f'README.md 「훅」 표 {listed} 가 hooks/hooks.json {hooks} 와 다르다')
    counts = {'원칙': len(principles), '플레이북': len(glob.glob('skills/mode/playbooks/*.md'))}
    for word, n in counts.items():
        for m in re.finditer(rf'{word} (\d+)개', readme):
            if int(m.group(1)) != n:
                errors.append(f'README.md: 「{m.group(0)}」 인데 실제로는 {n}개다')
    owner = {r'어렵다는 것만으로는|두 번 다 검사를 못 넘': 'skills/mode/SKILL.md'}
    for path in glob.glob('skills/**/*.md', recursive=True) + glob.glob('agents/*.md') + ['docs/authoring.md']:
        for i, line in enumerate(open(path).read().splitlines(), 1):
            if re.search(r'plugins/cache/[\w*.-]+/[\w*.-]+/\*', line):
                errors.append(f'{path}:{i}: 설치 폴더를 이름과 판으로 짐작하지 않는다. 스킬은 자기 폴더를, 에이전트는 installed_plugins.json 의 installPath 를 쓴다')
            if re.match(r'\| `(hooks/)?[\w-]+\.py`', line) and line.split('`')[1].split('/')[-1] in hooks:
                errors.append(f'{path}:{i}: 훅 표는 README.md 「훅」 절에만 둔다')
            for pattern, home in owner.items():
                if path != home and re.search(pattern, line):
                    errors.append(f'{path}:{i}: 이 규칙은 {home} 에만 쓰고 여기서는 그 절을 가리킨다')


def check_evals():
    for name in ('mode', 'correct', 'idea'):
        if not os.path.exists(f'evals/{name}.md'):
            errors.append(f'evals/{name}.md 없음. 스킬 글을 줄이기 전에 지킬 결정을 상황으로 적어 둔다')
    for path in glob.glob('evals/*.md'):
        cases = re.split(r'^## ', open(path).read(), flags=re.M)[1:]
        if len(cases) < 2:
            errors.append(f'{path}: 상황이 2개보다 적다')
        for case in cases:
            title = case.splitlines()[0]
            for field in ('- 상황: ', '- 기대 결정: ', '- 근거: '):
                if field not in case:
                    errors.append(f'{path} 「{title}」: {field.strip()} 줄이 없다')
            for src, quote in re.findall(r'^- 근거: `([^`]+)` 「(.+)」$', case, re.M):
                if quote not in (open(src).read() if os.path.exists(src) else ''):
                    errors.append(f'{path} 「{title}」: 근거 문장이 {src} 에서 사라졌다. 일부러 뺐으면 이 상황의 기대 결정도 고친다: {quote}')


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
        if os.path.isfile(path):
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


def git_version(rev):
    r = subprocess.run(['git', 'show', f'{rev}:{PJ}'], capture_output=True, text=True)
    return json.loads(r.stdout)['version'] if r.returncode == 0 else None


def check_version_bumps_last_digit_by_one():
    dirty = subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', PJ]).returncode != 0
    old, new = git_version('HEAD' if dirty else 'HEAD~1'), json.load(open(PJ))['version']
    if old and old != new:
        o, n = [list(map(int, v.split('.'))) for v in (old, new)]
        if n[:2] != o[:2] or n[2] != o[2] + 1:
            errors.append(f'{PJ}: 판 {old} → {new}. 끝자리만 1 올린다({old} → {".".join(map(str, o[:2] + [o[2] + 1]))})')


def run_self_tests():
    for cmd in (['scripts/test_hooks.py'], ['skills/no-comments/scripts/count.py', '--self-test'], ['skills/featuremap/scripts/featuremap.py', '--self-test'], ['.claude/skills/upstream/upstream.py', '--self-test'], ['scripts/shrink.py', '--self-test']):
        r = subprocess.run([sys.executable, '-I', *cmd], capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stdout + r.stderr)


skills = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob('skills/*/SKILL.md'))
agents = sorted(os.path.basename(p)[:-3] for p in glob.glob('agents/*.md'))
check_manifests_parse()
check_frontmatter(skills, agents)
principles = load_principles()
check_old_names_and_references(skills, agents, principles)
check_required_sentences()
check_single_source(principles)
check_evals()
check_no_private_words()
check_author_email_is_noreply()
check_version_bumps_last_digit_by_one()
if errors:
    sys.exit('\n'.join(errors))
run_self_tests()
print(f'OK 스킬 {len(skills)} · 에이전트 {len(agents)} · 원칙 {len(principles)}')
