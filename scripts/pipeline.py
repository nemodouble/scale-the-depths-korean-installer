"""Read-only extraction and validated translation assembly for Scale the Depths."""
from __future__ import annotations
import argparse, collections, hashlib, json, os, pathlib, re, sys
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')

ROOT = pathlib.Path(__file__).resolve().parents[1]
GAME = pathlib.Path(os.environ.get('SCALE_DEPTHS_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\Scale the Depths')).expanduser().resolve()
AA = pathlib.Path('Scale The Depths_Data/StreamingAssets/aa')
EN = 'localization-string-tables-english(en)_assets_all.bundle'

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write_json(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def read_json(p): return json.loads(p.read_text(encoding='utf-8'))
def words(s): return len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", s))

def extract():
    import UnityPy
    directory = GAME / AA / 'StandaloneWindows64'
    shared = {o.path_id:o.read_typetree() for o in UnityPy.load(str(directory/'localization-assets-shared_assets_all.bundle')).objects if o.type.name=='MonoBehaviour'}
    rows=[]; tables=[]
    for o in UnityPy.load(str(directory/EN)).objects:
        if o.type.name!='MonoBehaviour': continue
        d=o.read_typetree(); sh=shared[d['m_SharedData']['m_PathID']]
        keys={r['m_Id']:r['m_Key'] for r in sh['m_Entries']}
        table=d['m_Name'].removesuffix('_en')
        for r in d['m_TableData']:
            rows.append(dict(table=table,id=str(r['m_Id']),key=keys.get(r['m_Id']),source=r['m_Localized'],target=None,status='pending',notes=''))
        texts=[r['m_Localized'] for r in d['m_TableData']]
        tables.append(dict(table=table,entries=len(texts),words=sum(map(words,texts)),chars=sum(map(len,texts))))
    rows.sort(key=lambda r:(r['table'],int(r['id'])))
    for n,r in enumerate(rows): r['index']=n
    write_json(ROOT/'source/english.json',rows)
    write_json(ROOT/'source/statistics.json',dict(tables=tables,entries=len(rows),words=sum(words(r['source']) for r in rows),unique=len(set(r['source'] for r in rows if r['source'].strip()))))
    paths=[GAME/AA/'catalog.json', directory/EN, directory/'localization-assets-shared_assets_all.bundle',directory/'localization-asset-tables-english(en)_assets_all.bundle',GAME/'GameAssembly.dll']
    write_json(ROOT/'source/manifest.json',dict(game=str(GAME),files={str(p.relative_to(GAME)):dict(sha256=digest(p),size=p.stat().st_size) for p in paths}))
    (ROOT/'translations').mkdir(exist_ok=True)
    print(json.dumps(dict(entries=len(rows),words=sum(words(r['source']) for r in rows))))

def assemble(complete=False):
    rows=read_json(ROOT/'source/english.json'); byindex={r['index']:r for r in rows}; seen=set(); errors=[]
    for p in sorted((ROOT/'translations').glob('*.json')):
        for index,target in read_json(p).items():
            index=int(index)
            if index in seen: errors.append(f'duplicate index {index}')
            seen.add(index)
            if index not in byindex: errors.append(f'unknown index {index}');continue
            r=byindex[index]
            if not isinstance(target,str): errors.append(f'non-string target {index}');continue
            r['target']=target;r['status']='translated'
            if r['source'].strip() and not target.strip(): errors.append(f'empty target {index}')
            # Preserve exact format expressions, including the unusual {""} source.
            if collections.Counter(re.findall(r'\{[^{}]*\}',r['source']))!=collections.Counter(re.findall(r'\{[^{}]*\}',target)): errors.append(f'placeholder mismatch {index}')
    for r in rows:
        if not r['source'].strip():r['target']=r['source'];r['status']='preserved_empty'
    pending=[r['index'] for r in rows if r['target'] is None]
    if complete and pending: errors.append(f'{len(pending)} entries pending')
    report=dict(total=len(rows),translated=len(seen),pending=len(pending),errors=errors)
    write_json(ROOT/'reports/validation.json',report)
    out=ROOT/'work/translation.jsonl';out.parent.mkdir(exist_ok=True)
    out.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    if errors: raise SystemExit(1)
    return rows

def show(table=None,start=None,end=None):
    for r in read_json(ROOT/'source/english.json'):
        if table and table.lower() not in r['table'].lower():continue
        if start is not None and r['index']<start:continue
        if end is not None and r['index']>=end:continue
        print(json.dumps({k:r[k] for k in ('index','table','key','source')},ensure_ascii=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['extract','validate','show']);ap.add_argument('--complete',action='store_true');ap.add_argument('--table');ap.add_argument('--start',type=int);ap.add_argument('--end',type=int);a=ap.parse_args()
    if a.command=='extract':extract()
    elif a.command=='validate':assemble(a.complete)
    else:show(a.table,a.start,a.end)
