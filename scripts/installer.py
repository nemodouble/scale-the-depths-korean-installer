"""Standalone, offline Windows delta installer and restore tool."""
import argparse, hashlib, json, os, pathlib, shutil, sys, tempfile
import bsdiff4

def sha(data): return hashlib.sha256(data).hexdigest()

def ensure_game_closed():
    if sys.platform!='win32':return
    import ctypes
    from ctypes import wintypes as w
    class Entry(ctypes.Structure):
        _fields_=[('size',w.DWORD),('usage',w.DWORD),('pid',w.DWORD),('heap',ctypes.c_size_t),('module',w.DWORD),('threads',w.DWORD),('parent',w.DWORD),('priority',w.LONG),('flags',w.DWORD),('exe',w.WCHAR*260)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD];kernel.CreateToolhelp32Snapshot.restype=w.HANDLE
    kernel.Process32FirstW.argtypes=[w.HANDLE,ctypes.POINTER(Entry)];kernel.Process32NextW.argtypes=[w.HANDLE,ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes=[w.HANDLE]
    handle=kernel.CreateToolhelp32Snapshot(2,0)
    if handle==ctypes.c_void_p(-1).value:raise RuntimeError('실행 중인 게임을 확인하지 못했습니다. 잠시 후 다시 시도하세요.')
    try:
        entry=Entry();entry.size=ctypes.sizeof(entry)
        ok=kernel.Process32FirstW(handle,ctypes.byref(entry))
        if not ok:raise RuntimeError('실행 중인 프로그램 확인에 실패했습니다.')
        while ok:
            if entry.exe.casefold()=='scale the depths.exe':raise RuntimeError('Scale the Depths를 먼저 종료하세요. 실행 중에는 설치·복구할 수 없습니다.')
            ok=kernel.Process32NextW(handle,ctypes.byref(entry))
    finally:kernel.CloseHandle(handle)
def checked(root,relative):
    root=root.resolve();p=(root/relative).resolve()
    if not p.is_relative_to(root):raise ValueError('Unsafe package path')
    return p

def operate(game,package,restore=False):
    ensure_game_closed()
    game=pathlib.Path(game).resolve();package=pathlib.Path(package).resolve()
    m=json.loads((package/'manifest.json').read_text(encoding='utf-8'))
    if m.get('preview'):raise RuntimeError('개발용 시험본은 배포 설치 도구로 설치할 수 없습니다.')
    backup=game/'KoreanPatch_Backup'
    pending=[]
    # Validate all files and reconstruct every result before modifying anything.
    for f in m['files']:
        p=checked(game,f['path']);b=checked(backup,f['path'])
        current=p.read_bytes();current_hash=sha(current)
        if current_hash not in (f['before'],f['after']):
            raise RuntimeError(f"지원하지 않는 버전 또는 수정된 파일입니다: {f['path']}")
        if b.exists() and sha(b.read_bytes())!=f['before']:
            raise RuntimeError(f"원본 백업이 손상되었습니다: {f['path']}")
        if restore:
            if current_hash==f['before']:continue
            if not b.exists():raise RuntimeError(f"원본 백업이 없습니다: {f['path']}")
            result=b.read_bytes();expected=f['before']
        else:
            if current_hash==f['after']:
                if not b.exists():raise RuntimeError(f"패치는 적용되어 있지만 원본 백업이 없습니다. Steam에서 원본을 복구한 뒤 다시 설치하세요: {f['path']}")
                continue
            delta=checked(package,f['delta']).read_bytes()
            if sha(delta)!=f['delta_sha256']:raise RuntimeError('패치 파일이 손상되었습니다.')
            result=bsdiff4.patch(current,delta);expected=f['after']
        if sha(result)!=expected:raise RuntimeError('패치 결과 검증에 실패했습니다.')
        pending.append((p,b,current,result,f))
    if not pending:return '이미 복구되어 있습니다.' if restore else '이미 설치되어 있습니다.'
    ensure_game_closed()
    backup.mkdir(parents=True,exist_ok=True)
    staged=[];committed=[]
    try:
        for p,b,current,result,f in pending:
            if not b.exists():
                if restore:raise RuntimeError('원본 백업이 없습니다.')
                b.parent.mkdir(parents=True,exist_ok=True)
                with b.open('xb') as out:out.write(current)
            fd,name=tempfile.mkstemp(prefix='.korean-patch-',dir=p.parent)
            with os.fdopen(fd,'wb') as out:out.write(result)
            staged.append((pathlib.Path(name),p,current))
        for temp,p,current in staged:
            os.replace(temp,p);committed.append((p,current))
        for p,b,current,result,f in pending:
            if sha(p.read_bytes())!=sha(result):raise RuntimeError('설치 후 파일 검증에 실패했습니다.')
    except Exception:
        # Roll back only files this transaction actually replaced.
        for p,current in reversed(committed):p.write_bytes(current)
        raise
    finally:
        for temp,p,current in staged:
            if temp.exists():temp.unlink()
    return '원본 복구가 완료되었습니다.' if restore else '설치가 완료되었습니다. 게임 언어에서 한국어(패치)를 선택하세요.'

def gui(package):
    import tkinter as tk
    from tkinter import filedialog,messagebox
    root=tk.Tk();root.title('Scale the Depths 한국어 패치');root.geometry('650x245')
    path=tk.StringVar(value=r'C:\Program Files (x86)\Steam\steamapps\common\Scale the Depths')
    tk.Label(root,text='게임을 종료한 뒤 정식 버전 설치 폴더를 선택하세요.').pack(pady=12)
    tk.Entry(root,textvariable=path,width=86).pack(padx=12)
    def browse():
        selected=filedialog.askdirectory()
        if selected:path.set(selected)
    tk.Button(root,text='게임 폴더 선택',command=browse).pack(pady=8)
    status=tk.StringVar(value='원본 파일을 백업하고 지원 버전을 검사합니다.')
    def action(restore):
        try:status.set(operate(path.get(),package,restore));messagebox.showinfo('완료',status.get())
        except Exception as exc:messagebox.showerror('적용하지 못했습니다',str(exc))
    frame=tk.Frame(root);frame.pack(pady=8)
    tk.Button(frame,text='한국어 패치 설치',command=lambda:action(False)).pack(side='left',padx=10)
    tk.Button(frame,text='원본 복구',command=lambda:action(True)).pack(side='left',padx=10)
    tk.Label(root,textvariable=status,wraplength=620).pack(pady=10)
    root.mainloop()

if __name__=='__main__':
    default=pathlib.Path(sys.executable if getattr(sys,'frozen',False) else __file__).resolve().parent
    ap=argparse.ArgumentParser();ap.add_argument('--game');ap.add_argument('--package',type=pathlib.Path,default=default);ap.add_argument('--restore',action='store_true');args=ap.parse_args()
    if args.game:print(operate(args.game,args.package,args.restore))
    else:gui(args.package)
