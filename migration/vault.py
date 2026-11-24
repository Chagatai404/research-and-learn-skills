"""Stage, verify, apply or restore one migration batch."""
import argparse
from collections import Counter
import json
import re
from pathlib import Path

from collection import ARCHIVE, generate, group, HUB, page_path, PILOT, wik
from storage import checked, current, digest, restore_drill, transfer

WIKI = re.compile(r'!?\[\[([^\]\n]+?)\]\]')
VAULT = Path('C:/Users/ASUS/Obsidian/Knowledge')
WORK = Path(__file__).resolve().parents[1] / '.migration'
PROJECTION = 'Research OS/Knowledge/Knowledge.md'
APP_NOTE = '01 Projects/Scientific Research OS/Scientific Research OS.md'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def inventory(vault):
    notes, hashes = {}, {}
    for f in vault.rglob('*.md'):
        rel = f.relative_to(vault).as_posix()
        if any(part.startswith('.') for part in f.relative_to(vault).parts): continue
        checked(vault,rel)
        data=f.read_bytes()
        notes[rel]=data.decode('utf-8-sig').replace('\r\n','\n')
        hashes[rel]=digest(data)
    return notes, hashes


def resolve(token, source, paths):
    dest, _, anchor = token.split('|',1)[0].partition('#')
    if not dest: dest=source
    parent = Path(source).parent.as_posix()
    candidates = [dest,parent+'/'+dest] if '/' in dest else [parent+'/'+dest,dest]
    for c in candidates:
        for rel in (c,c+'.md'):
            if rel in paths: return rel,anchor
    if '/' not in dest:
        matches=[p for p in paths if p.endswith('/'+dest) or p.endswith('/'+dest+'.md')]
        if len(matches)==1:return matches[0],anchor
    return None,anchor


def qualify_links(body, source, files):
    """Resolve duplicate short names within one authored course by directory distance."""
    def qualify(match):
        token = match[1]
        dest, sep, alias = token.partition('|')
        target, sep2, anchor = dest.partition('#')
        if not target or '/' in target or resolve(token,source,files)[0]:
            return match[0]
        parent = Path(source).parent
        same_course = '/'.join(source.split('/')[:2])+'/'
        matches = [Path(p) for p in files if p.startswith(same_course) and Path(p).name in (target,target+'.md')]
        if not matches:
            return match[0]
        def distance(candidate):
            shared = 0
            for a,b in zip(candidate.parent.parts,parent.parts):
                if a!=b:break
                shared+=1
            return len(candidate.parent.parts)+len(parent.parts)-2*shared
        best = min(map(distance,matches))
        choices = [p for p in matches if distance(p)==best]
        if len(choices)!=1:
            return match[0]
        new = choices[0].as_posix()
        if new.endswith('.md'):new=new[:-3]
        return ('!' if match[0].startswith('!') else '')+'[['+new+sep2+anchor+'|'+(alias if sep else dest)+']]'
    return WIKI.sub(qualify,body)


def links(vault, notes, output, sources):
    files=set(p.relative_to(vault).as_posix() for p in vault.rglob('*') if p.is_file())
    files.update(output)
    inherited=[]
    verified=0
    for path in sorted(set(output)|set(sources)):
        old = Counter(WIKI.findall(notes.get(path,'')))
        for token in WIKI.findall(output.get(path,notes.get(path,''))):
            target, anchor = resolve(token,path,files)
            issue=None
            if not target: issue='missing or ambiguous target'
            elif anchor and target.endswith('.md'):
                txt=output.get(target,notes.get(target,''))
                if anchor.startswith('^'):
                    if not re.search(r'\^'+re.escape(anchor[1:])+r'(?:\s|$)',txt):issue='missing block'
                elif anchor.casefold() not in {m.strip().casefold() for m in re.findall(r'^#{1,6} (.+)$',txt,re.M)}:
                    issue='missing heading'
            if old[token]:
                old[token]-=1
                if issue: inherited.append({'source':path,'link':token,'reason':issue})
            elif issue:
                raise ValueError(f'New broken link in {path}: {token} ({issue})')
            else:
                verified+=1
    return verified,inherited


def stage(vault, folder, batch):
    notes, hashes=inventory(vault)
    output, sources=generate(notes,batch)
    for rel in sources:
        if rel.startswith('01 Projects/') and '/Sources/' not in rel:
            before=output.get(rel,notes[rel])
            fixed=qualify_links(before,rel,set(notes))
            if before!=fixed:output[rel]=fixed
    stage_output(vault, folder, batch, notes, hashes, output, sources)


def stage_output(vault, folder, batch, notes, hashes, output, sources, refreshed=None):
    if folder.exists():raise ValueError('Batch exists. Use its checked manifest or choose an empty private work folder.')
    count, inherited=links(vault,notes,output,sources)
    changes=[]
    folder.mkdir(parents=True)
    for rel, text in output.items():
        target=checked(vault,rel)
        if rel.startswith('Study and Research/') and target.exists() and batch!='cleanup' and not (batch=='remaining' and rel==page_path(PILOT)):
            raise ValueError('Destination already exists: '+rel)
        old=target.read_bytes() if target.exists() else None
        if old is not None and digest(old)!=hashes[rel]:
            raise ValueError('Concurrent edit: '+rel)
        data=text.encode('utf-8')
        if old is not None:
            if old.startswith(b'\xef\xbb\xbf'):data=b'\xef\xbb\xbf'+data
            if b'\r\n' in old and b'\n' not in old.replace(b'\r\n',b''):
                data=data.replace(b'\n',b'\r\n')
            backup=checked(folder/'before',rel)
            backup.parent.mkdir(parents=True,exist_ok=True)
            backup.write_bytes(old)
        dest=checked(folder/'after',rel)
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(data)
        changes.append({'path':rel,'before':digest(old) if old is not None else None,'after':digest(data)})
    for rel, record in sources.items():
        record['sha256']=hashes[rel]
        record['source']=rel
        dest=output.get(record['destination'])
        if dest is None or '## '+record['section']+'\n' not in dest:
            raise ValueError('Unmapped source: '+rel)
    manifest={'version':1,'batch':batch,'vault':str(vault.resolve()),'sources':sources,'changes':changes,
              'new_links_verified':count,'inherited_link_issues':len(inherited)}
    if refreshed:
        manifest['refreshed_sources']=refreshed
    save(folder/'manifest.json',manifest)
    save(folder/'inherited-links.json',inherited)
    restore_drill(folder,changes)
    (folder/'verified.sha256').write_text(current(folder/'manifest.json'),encoding='ascii')
    print(f'{batch}: staged {len(sources)} original notes, {len(changes)} destination writes, {count} new links verified, {len(inherited)} inherited link issues. Restore drill passed.')


def replace_once(body, old, new):
    if body.count(old)!=1:
        raise ValueError('Expected one occurrence of '+repr(old))
    return body.replace(old,new,1)


def stage_cleanup(vault, work):
    notes, hashes=inventory(vault)
    pilot=read_verified(work/'pilot',vault)
    remaining=read_verified(work/'remaining',vault)
    if any(not (work/m['batch']/'applied').is_file() for m in (pilot,remaining)):
        raise ValueError('Apply both migration batches before cleanup')
    mapped=pilot['sources'] | remaining['sources']
    fresh={name for name,body in notes.items() if not name.startswith('Study and Research/') and group(name,body)}-mapped.keys()
    if any(not re.fullmatch(r'Research OS/Reviews/2026-11-24(?: [\w-]+)?\.md',name) for name in fresh):
        raise ValueError('Unexpected source paths: '+repr(sorted(fresh)))
    historical=page_path(ARCHIVE)
    records={name:{'destination':historical,'section':'Review history'} for name in sorted(fresh)}
    output={}
    if records:
        items='\n'.join('- '+wik(name,Path(name).stem) for name in records)
        output[historical]=replace_once(notes[historical],'## Review history\n\n','## Review history\n\n'+items+'\n')

    home=notes['Home.md']
    app=re.search(r'^- \[\[Scientific Research OS\]\] [^\n]+\n',home,re.M)
    if not app:
        raise ValueError('Missing old app entry on Home')
    home=replace_once(home,app[0],'')
    home=home.replace('[[AMS ECAL QML]]',wik('01 Projects/AMS ECAL QML/AMS ECAL QML.md','AMS ECAL QML'))
    home=replace_once(home,'[[ROC AUC]]',wik('02 Knowledge/Machine Learning/ROC AUC.md','ROC AUC'))
    home=replace_once(home,'- [[01 Projects/Scientific Research OS/Material Index|Scientific Research OS]]\n','')
    home=replace_once(home,'Generated app projections remain under Research OS; authored notes above are the canonical vault material.\n<!-- research-os:navigation:end -->',
                      '<!-- research-os:navigation:end -->\n\n## Retired tooling\n\n- '+wik(APP_NOTE,'Scientific Research OS')+' · historical project notes. Earlier app exports are available in '+wik(historical,'Historical material')+'.')
    output['Home.md']=home
    app_body=replace_once(notes[APP_NOTE],'\nstatus: active\n','\nstatus: retired\n')
    output[APP_NOTE]=replace_once(app_body,'## What it is',
                                 'The app is retired. Open '+wik(HUB,'Study and Research')+' to continue in Obsidian. The notes below document the earlier app.\n\n## What it is')

    for name, record in remaining['sources'].items():
        if '/Investigation - ' not in record['destination'] or not name.startswith('Research OS/'):
            continue
        metadata=re.search(r'^ros_portal: "(http://127\.0\.0\.1:8737/[^"\n]+)"\n',notes[name],re.M)
        if not metadata:
            raise ValueError('Missing retired portal metadata: '+name)
        body=replace_once(notes[name],metadata[0],'')
        output[name]=replace_once(body,'[Open in the portal]('+metadata[1]+')\n','')

    expected={name:r['sha256'] for name,r in mapped.items()}
    for m in (pilot,remaining):
        expected.update({e['path']:e['after'] for e in m['changes']})
    drift={name for name,sha in expected.items() if hashes.get(name)!=sha}
    refreshed={}
    if drift:
        if drift!={PROJECTION} or '\nros_status: generated\n' not in notes.get(PROJECTION,''):
            raise ValueError('Unexpected source changes: '+repr(sorted(drift)))
        refreshed[PROJECTION]={'before':expected[PROJECTION],'after':hashes[PROJECTION],
                               'reason':'Generated Knowledge index refreshed after the migration snapshot'}
    stage_output(vault,work/'cleanup','cleanup',notes,hashes,output,records,refreshed)


def read_verified(folder,vault):
    if (folder/'verified.sha256').read_text(encoding='ascii')!=current(folder/'manifest.json'):
        raise ValueError('Manifest does not match restore-drilled revision')
    m=json.loads((folder/'manifest.json').read_text(encoding='utf8'))
    if m['vault']!=str(vault.resolve()):raise ValueError('Wrong vault')
    return m


def apply(vault,folder):
    m=read_verified(folder,vault)
    writes={e['path']:e['after'] for e in m['changes']}
    for name,record in m['sources'].items():
        if current(checked(vault,name)) not in {record['sha256'],writes.get(name,'')}:
            raise ValueError('Original changed since preview: '+name)
    for name,record in m.get('refreshed_sources',{}).items():
        if current(checked(vault,name))!=record['after']:
            raise ValueError('Generated index changed since preview: '+name)
    transfer(vault,folder)
    verify(vault,folder)


def verify(vault,folder):
    m=read_verified(folder,vault)
    expected={name:r['sha256'] for name,r in m['sources'].items()}
    expected.update({e['path']:e['after'] for e in m['changes']})
    expected.update({name:r['after'] for name,r in m.get('refreshed_sources',{}).items()})
    for name,sha in expected.items():
        if current(checked(vault,name))!=sha:raise ValueError('Verification failed: '+name)
    notes,_=inventory(vault)
    # Recheck every new link against live targets, including unchanged binary attachments.
    original={e['path']:checked(folder/'before',e['path']).read_text(encoding='utf-8-sig') if e['before'] else '' for e in m['changes']}
    existing=dict(notes)
    existing.update(original)
    count,_=links(vault,existing,{e['path']:notes[e['path']] for e in m['changes']},m['sources'])
    if count!=m['new_links_verified']:raise ValueError('New link count mismatch')
    print(f"{m['batch']}: verified {len(expected)} live notes and {count} introduced links.")


def verify_all(vault, work):
    """Reconcile original note identities and the final state across overlapping edits."""
    expected, inputs, generated = {}, {}, {}
    batches=['pilot','remaining']
    if (work/'cleanup'/'applied').is_file():
        batches.append('cleanup')
    refreshed={}
    for batch in batches:
        folder=work/batch
        m=read_verified(folder,vault)
        for name,record in m['sources'].items():
            if name in inputs:raise ValueError('Duplicate source mapping: '+name)
            inputs[name]=record
            expected[name]=record['sha256']
        for entry in m['changes']:
            name=entry['path']
            if name in expected and expected[name]!=entry['before']:
                raise ValueError('Broken batch chain: '+name)
            expected[name]=generated[name]=entry['after']
        for name,record in m.get('refreshed_sources',{}).items():
            if name not in inputs or name in generated or expected[name]!=record['before']:
                raise ValueError('Unmatched refreshed source: '+name)
            expected[name]=record['after']
            refreshed[name]=record
    notes,_=inventory(vault)
    eligible={name for name, body in notes.items() if not name.startswith('Study and Research/') and group(name,body)}
    if diff:=eligible.symmetric_difference(inputs):
        raise ValueError('Unreconciled source paths: '+repr(sorted(diff)))
    for name,sha in expected.items():
        if current(checked(vault,name))!=sha:raise ValueError('Final content mismatch: '+name)
    for name,record in inputs.items():
        target=record['destination']
        marker='\n## '+record['section']+'\n'
        section=('\n'+notes[target]).partition(marker)[2].partition('\n## ')[0]
        occurrences=sum(resolve(token,target,notes)[0]==name for token in WIKI.findall(section))
        if occurrences!=1:
            raise ValueError('Expected one link from its mapped section: '+name)
    # Compare final links against their pre-migration baseline. A missing or
    # changed attachment/heading is caught even when its source is unchanged.
    baseline=dict(notes)
    for batch in reversed(batches):
        folder=work/batch
        for e in read_verified(folder,vault)['changes']:
            baseline[e['path']]=(checked(folder/'before',e['path']).read_text(encoding='utf-8-sig')
                                 if e['before'] else '')
    count,existing=links(vault,baseline,{n:notes[n] for n in generated},inputs)
    print(f'Final reconciliation: {len(inputs)} original notes mapped exactly once; {len(generated)} distinct note writes; {len(expected)} final hashes verified; {count} new wiki links resolve; {len(existing)} inherited link occurrences for review.')
    save(work/'final-check.json',{'sources':len(inputs),'changed_notes':len(generated),'verified_hashes':len(expected),
                                 'verified_new_wiki_links':count,'inherited_link_issues':existing,'refreshed_sources':refreshed})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['stage','apply','verify','restore','reconcile'])
    parser.add_argument('batch',choices=['pilot','remaining','cleanup'],nargs='?')
    parser.add_argument('--vault',type=Path,default=VAULT)
    parser.add_argument('--work',type=Path,default=WORK)
    args=parser.parse_args()
    vault=args.vault.resolve()
    work=args.work.resolve()
    if work.is_relative_to(vault) or vault.is_relative_to(work):raise ValueError('Use a separate private work folder')
    if args.action=='reconcile':
        verify_all(vault,work)
        return
    if args.batch is None:parser.error('select pilot or remaining')
    folder=work/args.batch
    if args.action=='stage':
        if args.batch=='remaining':verify(vault,work/'pilot')
        if args.batch=='cleanup':stage_cleanup(vault,work)
        else:stage(vault,folder,args.batch)
    elif args.action=='apply':
        if args.batch=='remaining' and not (folder/'applied').exists():
            pp=read_verified(work/'pilot',vault)
            # After partial apply the pilot backlink may already have been updated.
            expected=next(e for e in pp['changes'] if e['path']==page_path(PILOT))['after']
            if current(checked(vault,page_path(PILOT)))==expected:verify(vault,work/'pilot')
        apply(vault,folder)
        (folder/'applied').write_text('verified\n',encoding='ascii')
    elif args.action=='verify':verify(vault,folder)
    else:
        read_verified(folder,vault)
        transfer(vault,folder,reverse=True)
        (folder/'applied').unlink(missing_ok=True)
        print('Original note hashes restored. Newly created empty directories may remain.')


if __name__=='__main__':main()
