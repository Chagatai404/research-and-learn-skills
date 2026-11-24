"""Build the human navigation and in-note practice surfaces from the existing collection."""
from collections import defaultdict
from pathlib import PurePosixPath
import re

ROOT = 'Study and Research'
HUB = ROOT + '/Study and Research.md'
PILOT = 'CENG487 Quantum Computing'
WEEKS = (
    ('Introduction to linear statistical models', 'For two observations with the same predictor value, what can differ even if the model is correct?'),
    ('Simple linear model estimation', 'Why does fitting an intercept make the least-squares residuals sum to zero?'),
    ('Simple linear model goodness of fit', 'Can a large R-squared coexist with systematic residual curvature? Explain.'),
    ('Hypothesis tests in simple regression and quiz 1', 'What hypothesis does the slope t-test address, and which standard error does it use?'),
    ('Assumptions and diagnostics', 'What would a widening band in a residual-versus-fitted plot lead you to investigate?'),
    ('Two-predictor estimation', 'Interpret a slope when the other predictor is held fixed.'),
    ('Multiple regression fit and tests', 'What does an overall F-test establish when there are two slopes?'),
    ('Midterm examination', 'Reconstruct a fitted model, an inference and a diagnostic from one example.'),
    ('Matrix formulation for several predictors', 'What do the rows and columns of the design matrix represent?'),
    ('Estimation, fit and hypothesis tests', 'How would you compare two nested regression models?'),
    ('Multicollinearity and misspecification', 'How could a stable fitted response coexist with unstable individual coefficients?'),
    ('Model building, selection and quiz 2', 'How would you evaluate a model selected after trying several alternatives?'),
    ('Linear models with dummy variables', 'How does changing the reference group alter the intercept and fitted values?'),
    ('Transformations for linearizable models', 'After fitting a log-response model, what must you consider when reporting results on the original scale?'),
)
CENG_PROBES = (
    'For the vectors (1, i) and (1, −i), how would you test orthogonality? Explain which entries you conjugate.',
    'How would you distinguish a global phase change from a relative phase change in a two-component state?',
    'After a projective measurement gives one specified outcome, how do you obtain the conditional state?',
    'Compare (|00⟩ + |11⟩)/√2 with (|00⟩ + |01⟩)/√2. How could you decide which state factors?',
    'How would you calculate the probability of seeing 1 on just the first wire of a two-qubit circuit?',
    'Which steps of teleportation require Alice’s classical message, and what can Bob predict before it arrives?',
    'Which property of an oracle does Deutsch–Jozsa test, and where does interference enter the argument?',
)
COURSES = {
    'ceng301': 'CENG301 Data Structures', 'ceng487': PILOT, 'stat250':'STAT250',
    'stat291':'STAT291 Statistical Computing', 'stat303':'STAT303 Mathematical Statistics I',
    'stat363':'STAT363 Linear Models I',
}
RESEARCH = ('AMS ECAL QML', 'Knee Abnormality ML', 'Realistic-regime multiscale research')
REFERENCE = 'Shared reading'
ARCHIVE = 'Historical material'
UNCERTAIN = 'Material to identify'


def wik(path, title=None, anchor=None):
    dest = path[:-3] if path.endswith('.md') else path
    label = title or PurePosixPath(dest).name
    label = re.sub(r'[\[\]|\r\n]', ' ', label)
    return '[[' + dest + ('#'+anchor if anchor else '') + '|' + label + ']]'


def group(name, body):
    lower = name.lower().replace(' ', '')
    if name.startswith(('99 Archive/', 'Research OS/Reviews/')) or re.match(r'Research OS/Home[^/]*\.md$', name):
        return ARCHIVE
    if re.search(r'^project:.*AMS ECAL QML',body,re.M):
        return RESEARCH[0]
    if name.startswith('02 Knowledge/Software Engineering/') and 'CENG301' in body:
        return COURSES['ceng301']
    if name.startswith('01 Projects/Scientific Research OS/') or name.startswith('02 Knowledge/Software Engineering/'):
        return None
    for code, label in COURSES.items():
        if code in lower or re.search(r'^ros_id:.*?' + code, body, re.M|re.I):
            return label
    if 'workspace-49768553552c4618a92f' in name:
        return COURSES['stat363']  # the lesson in that collection explicitly names STAT363
    if 'everything recorded in the folders' in name:
        return UNCERTAIN
    if 'kneeabnormality' in lower:
        return RESEARCH[1]
    if 'realistic-regime multiscale' in name.lower():
        return RESEARCH[2]
    if ('ams' in lower or 'ecal' in lower or name.startswith('Research OS/Knowledge/Claims/')):
        return RESEARCH[0]
    if name.startswith('Research OS/Knowledge/Capabilities/'):
        return REFERENCE
    if name.startswith(('02 Knowledge/', '03 Sources/')):
        return REFERENCE
    if name.startswith('04 Decisions/'):
        return None
    if name.startswith(('Research OS/Courses/', 'Research OS/Projects/', 'Research OS/Inbox/')):
        return UNCERTAIN
    if name.startswith('Research OS/Knowledge/'):
        return ARCHIVE
    return None


def page_path(subject):
    section = 'Courses' if subject in COURSES.values() else 'Research' if subject in RESEARCH else 'Library'
    filename = subject if subject == PILOT else subject + ' index'
    return f'{ROOT}/{section}/{subject}/{filename}.md'


def category(name):
    if '/Sources/Study Materials/' in name or '/Backups/' in name:
        return 'Earlier source copies'
    for part, label in [
        ('/Reviews/', 'Review history'), ('/Questions/', 'Research questions'),
        ('/Experiments/', 'Experiments and results'), ('/Hypotheses/', 'Hypotheses'),
        ('/Claims/', 'Claims and audit records'), ('/Lessons/', 'Lessons and prior practice'),
        ('/Capabilities/', 'Capabilities and prerequisites'), ('/Topics/', 'Topic explanations'),
        ('/Handouts/', 'Handouts'), ('/Papers/', 'Papers'), ('/Sources/', 'Sources'),
        ('/Lecture Notes/', 'Lecture notes')]:
        if part in name:
            return label
    if 'Decision' in name:
        return 'Decision records'
    if re.search(r'/Lecture \d+\.md$', name):
        return 'Lecture notes'
    return 'Material and indexes'


def title(name, body):
    h = re.search(r'^# (.+)$', body, re.M)
    s = h[1].strip() if h else PurePosixPath(name).stem
    return s if len(s) <= 145 else s[:142].rstrip()+'…'


def practice(prompt):
    return '## Practice here\n\n' + prompt + '\n\n**My answer**\n\n'


def generate(notes, batch):
    subjects = defaultdict(list)
    for name, body in notes.items():
        key = group(name, body)
        if key and (key == PILOT) == (batch == 'pilot'):
            subjects[key].append(name)
    output, sources = {}, {}
    for subject, paths in sorted(subjects.items()):
        page = page_path(subject)
        inc = []
        if subject == PILOT:
            inc += ['The syllabus specifies topic order. The numbered lectures below follow the supplied material. Lecture 7 is a supplemental reconstruction. Calendar weeks are undocumented.']
        elif subject == COURSES['stat303']:
            inc += ['Follow the instructor’s scope in the course overview. The expanded 14-week plan has unconfirmed provenance, so the reading sequence uses the documented topics.']
        elif subject == COURSES['stat363']:
            inc += ['## Syllabus weeks', 'The original schedule is in '+wik('01 Projects/STAT363/Sources/Syllabus/Syllabus.jpeg','the instructor syllabus')+'.']
            lesson = next(p for p in paths if '/Lessons/Lesson 01' in p)
            sections = re.findall(r'^## (.+)$', notes[lesson], re.M)
            for n, (topic, probe) in enumerate(WEEKS,1):
                week = f'{ROOT}/Courses/{subject}/Week {n:02d} - {topic}.md'
                inc.append('- '+wik(week,f'Week {n} · {topic}'))
                chunks = [f'# Week {n} · {topic}', wik(page, 'Course index'), '## '+topic]
                if n <= 2:
                    for heading in sections[:2] if n==1 else sections[2:8]:
                        chunks.append('!'+wik(lesson,heading,heading))
                elif n <= 7:
                    # Source associations in the existing midterm preparation table.
                    prep = '01 Projects/STAT363/Midterm Preparation.md'
                    rows = [s for s in notes[prep].splitlines() if s.startswith('| '+str(n)+'.')]
                    for row in rows:
                        cells = [v.strip() for v in row.strip('|').split('|')]
                        if len(cells)==4:
                            chunks.extend([cells[1], 'Course material · '+cells[2], 'Textbook · '+cells[3]])
                    chunks.append(wik(prep,'Scope, examples and source corrections','Scope and priorities'))
                else:
                    chunks.append('The syllabus schedules this topic here. Detailed notes can be added as the course progresses.')
                chunks.extend([practice(probe), '## Sources', wik('01 Projects/STAT363/Sources/Syllabus/Syllabus.jpeg','Fall 2026–27 syllabus')+' · '+wik('01 Projects/STAT363/Sources/Source Index.md','Lecture and recitation sources')])
                output[week]='\n\n'.join(chunks).rstrip()+'\n'
        elif subject == UNCERTAIN:
            inc += ['These originals do not identify their course or investigation precisely enough to assign them.']
        elif subject == ARCHIVE:
            inc += ['Earlier versions and dated review snapshots are available below when you need to retrace a source.']
        elif subject in RESEARCH:
            inc += ['Follow a question into its linked hypotheses, experiments and decisions. Each claim retains its historical audit status.']
        by_category = defaultdict(list)
        for name in sorted(paths, key=str.casefold):
            body = notes[name]
            where = category(name)
            label = title(name, body)
            active = name.startswith('01 Projects/CENG487 Quantum Computing/Lecture ') and name.count('/')==2
            active |= bool(re.search(r'^01 Projects/STAT303 [^/]+/Lecture Notes/STAT303 \d\d ',name))
            if active:
                if '## Practice here' in body:
                    raise ValueError(f'Existing practice section requires reconciliation: {name}')
                prompt = (CENG_PROBES[int(re.search(r'Lecture (\d+)',name)[1])-1] if subject==PILOT else
                          'Choose one worked example above. Reconstruct its first nontrivial step from memory and explain the assumption that makes it valid.')
                output[name]=body.rstrip()+'\n\n'+wik(page,'Study index')+'\n\n'+practice(prompt)
            if '/Questions/' in name and subject in RESEARCH:
                # Keep stable question identity and its existing explicit evidence links.
                key = re.search(r'^ros_id: ["\']?question:([^"\'\r\n]+)',body,re.M)
                ref = re.sub(r'[^\w -]', '',key[1])[:60].strip() if key else PurePosixPath(name).stem[:50]
                investigation = str(PurePosixPath(page).parent / ('Investigation - '+ref+'.md'))
                chunks = [f'# {label}',wik(page,'Research index'),'## Question and evidence','!'+wik(name,label)]
                ids = set(re.findall(r'\bEXP-\d+\b',body))
                evidence = [p for p in paths if '/Claims/' in p and ids.intersection(re.findall(r'\bEXP-\d+\b',notes[p]))]
                if evidence:
                    chunks += ['## Claims citing a linked experiment','\n'.join('- '+wik(p,title(p,notes[p])) for p in evidence)]
                chunks += ['## Teach-back','Which result bears most directly on this question? Trace it to its inputs, explain one assumption, and describe an observation that would change your interpretation.','**My reasoning**']
                if investigation in output: raise ValueError('Duplicate investigation identity')
                output[investigation]='\n\n'.join(chunks)+'\n'
                by_category[where].append(wik(investigation,label))
                sources[name]={'destination':investigation, 'section':'Question and evidence'}
            else:
                by_category[where].append(wik(name,label))
                sources[name]={'destination':page, 'section':where}
        order = ['Lecture notes','Research questions','Hypotheses','Experiments and results','Claims and audit records','Decision records','Topic explanations','Lessons and prior practice','Material and indexes']
        for cat in sorted(by_category,key=lambda x:(order.index(x) if x in order else len(order),x)):
            links = by_category[cat]
            inc.extend(['## '+cat,'\n'.join('- '+s for s in links)])
        output[page]='\n\n'.join(['# '+subject, wik(HUB,'Study and research') if batch!='pilot' else '', *inc]).strip()+'\n'
    if batch=='remaining':
        paths=[PILOT,*sorted(subjects)]
        chunks=['# Study and research']
        for heading, choices in [('Courses',COURSES.values()),('Research projects',RESEARCH),('Reading and source history',(REFERENCE,UNCERTAIN,ARCHIVE))]:
            chunks.extend(['## '+heading,'\n'.join('- '+wik(page_path(key),key) for key in paths if key in choices)])
        output[HUB]='\n\n'.join(chunks)+'\n'
        home = notes['Home.md']
        key = '## Learning and research records'
        if key not in home: raise ValueError('Home navigation changed; review before editing')
        home = re.sub(r'## Learning and research records\r?\n.*?(?=\n(?:## |<!-- research-os:navigation)|\Z)',
                      '## Learning and research records\n\n'+wik(HUB,'Open the course and research indexes')+'. Continue practice in the current week, lecture or investigation.\n',
                      home,flags=re.S)
        # Also give the pilot a back-link, after its batch has been verified.
        pp=page_path(PILOT)
        old = notes[pp]
        output[pp]=old.replace('# '+PILOT+'\n','# '+PILOT+'\n\n'+wik(HUB,'Study and research')+'\n',1)
        output['Home.md']=home
    return output, sources
