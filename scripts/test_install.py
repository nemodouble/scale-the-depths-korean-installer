"""Development install/restore with original hash checks and immutable backups."""
import argparse, shutil
from pipeline import ROOT, GAME, read_json, digest

def run(restore=False):
    manifest=read_json(ROOT/'work/build-manifest.json')
    backup=ROOT/'work/original-backup'
    for f in manifest['files']:
        rel=f['path'];p=GAME/rel;b=backup/rel
        if b.exists():
            if digest(b)!=f['before']:raise RuntimeError(f'Backup mismatch: {rel}')
        elif restore:raise RuntimeError(f'Backup absent: {rel}')
        else:
            if digest(p)!=f['before']:raise RuntimeError(f'Original mismatch: {rel}')
            b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,b)
    for f in manifest['files']:
        rel=f['path'];p=GAME/rel;src=(backup if restore else ROOT/'work/staged')/rel
        expected=f['before'] if restore else f['after']
        if digest(src)!=expected:raise RuntimeError(f'Payload mismatch: {rel}')
        shutil.copy2(src,p)
        if digest(p)!=expected:raise RuntimeError(f'Write verification failed: {rel}')
    print('RESTORED' if restore else 'DEVELOPMENT PREVIEW INSTALLED')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--restore',action='store_true');run(ap.parse_args().restore)
