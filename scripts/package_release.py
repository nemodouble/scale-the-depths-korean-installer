"""Create only binary deltas; refuse incomplete translations and preview builds."""
import hashlib, shutil, subprocess, sys
import bsdiff4
from pipeline import ROOT, GAME, assemble, read_json, write_json, digest
from build_patch import original

def package():
    assemble(complete=True)
    manifest=read_json(ROOT/'work/build-manifest.json')
    if manifest['preview']:raise RuntimeError('Preview build cannot be released')
    out=ROOT/'dist/ScaleTheDepths-Korean'
    if out.exists():shutil.rmtree(out)
    out.mkdir(parents=True)
    records=[]
    for f in manifest['files']:
        src=original(GAME/f['path']);dst=ROOT/'work/staged'/f['path']
        if digest(src)!=f['before'] or digest(dst)!=f['after']:raise RuntimeError('Build/source hash mismatch')
        delta=bsdiff4.diff(src.read_bytes(),dst.read_bytes());name=f'payload/{len(records):02d}.bsdiff'
        target=out/name;target.parent.mkdir(exist_ok=True);target.write_bytes(delta)
        assert bsdiff4.patch(src.read_bytes(),delta)==dst.read_bytes()
        records.append(dict(**f,delta=name,delta_sha256=hashlib.sha256(delta).hexdigest()))
    font_style=manifest.get('font_style','noto')
    write_json(out/'manifest.json',dict(version='1.0.0',preview=False,font_style=font_style,files=records))
    if font_style=='galmuri':shutil.copy2(ROOT/'fonts/galmuri/package/dist/LICENSE.txt',out/'Galmuri-OFL.txt')
    else:shutil.copy2(ROOT/'fonts/OFL.txt',out/'NotoSansKR-OFL.txt')
    shutil.copy2(ROOT/'DISTRIBUTION.md',out/'사용안내.md')
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--uac-admin','--name','한국어패치','--distpath',str(out),'--workpath',str(ROOT/'work/pyinstaller'),'--specpath',str(ROOT/'work'),str(ROOT/'tools/installer.py')],check=True)
    archive=shutil.make_archive(str(ROOT/'dist/ScaleTheDepths-Korean-1.0.0'),'zip',out)
    print(archive)

if __name__=='__main__':package()
