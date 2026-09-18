"""Build staged bundles; never overwrite the installed game."""
import argparse, base64, hashlib, io, json, pathlib, struct
import UnityPy
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from pipeline import ROOT, GAME, AA, EN, assemble, digest, read_json, write_json

ZH='localization-assets-chinese(simplified)(zh-hans)_assets_all.bundle'
ENASSET='localization-asset-tables-english(en)_assets_all.bundle'
ZHASSET='localization-asset-tables-chinese(simplified)(zh-hans)_assets_all.bundle'

def original(p):
    backup=ROOT/'work/original-backup'/p.relative_to(GAME)
    return backup if backup.exists() else p

def save_bundle(env,p):
    p.parent.mkdir(parents=True,exist_ok=True)
    assert len(env.files)==1
    p.write_bytes(next(iter(env.files.values())).save(packer='lz4'))

def font_sources(font_style):
    if font_style=='noto':
        weights={'Light':400,'Medium':500,'SemiBold':600};result={}
        for label,weight in weights.items():
            path=ROOT/'fonts'/f'NotoSansKR-{weight}.ttf'
            if not path.exists():
                font=instantiateVariableFont(TTFont(ROOT/'fonts/NotoSansKR-variable.ttf'),{'wght':weight},inplace=True)
                font.save(path)
            result[label]=(path,'Noto Sans KR',label)
        return result
    if font_style=='galmuri':
        directory=ROOT/'fonts/galmuri/package/dist'
        return {
            'Light':(directory/'Galmuri11.ttf','Galmuri11','Regular'),
            'Medium':(directory/'Galmuri11.ttf','Galmuri11','Regular'),
            'SemiBold':(directory/'Galmuri11-Bold.ttf','Galmuri11','Bold'),
        }
    raise ValueError(f'Unknown font style: {font_style}')

def update_face_info(face,font_path,family,style):
    font=TTFont(font_path);head=font['head'];hhea=font['hhea'];os2=font['OS/2'];post=font['post']
    scale=face['m_PointSize']/head.unitsPerEm
    face.update(
        m_FamilyName=family,m_StyleName=style,m_UnitsPerEM=head.unitsPerEm,
        m_LineHeight=(hhea.ascent-hhea.descent+hhea.lineGap)*scale,
        m_AscentLine=hhea.ascent*scale,m_CapLine=getattr(os2,'sCapHeight',hhea.ascent)*scale,
        m_MeanLine=getattr(os2,'sxHeight',hhea.ascent/2)*scale,m_DescentLine=hhea.descent*scale,
        m_SuperscriptOffset=hhea.ascent*scale,m_SubscriptOffset=hhea.descent*scale,
        m_UnderlineOffset=post.underlinePosition*scale,m_UnderlineThickness=post.underlineThickness*scale,
        m_StrikethroughOffset=os2.yStrikeoutPosition*scale,m_StrikethroughThickness=os2.yStrikeoutSize*scale,
        m_TabWidth=font['hmtx'][font.getBestCmap()[32]][0]*scale,
    )

def build(preview=False,font_style='noto'):
    rows=assemble(complete=not preview)
    source=GAME/AA/'StandaloneWindows64'; stage=ROOT/'work/staged'; dest=stage/AA/'StandaloneWindows64'
    for rel,v in read_json(ROOT/'source/manifest.json')['files'].items():
        if digest(original(GAME/rel))!=v['sha256']:raise RuntimeError(f'Source version changed: {rel}')
    lookup={(r['table']+'_en',int(r['id'])):r['target'] for r in rows if r['target'] is not None}
    e=UnityPy.load(str(original(source/EN)))
    for o in e.objects:
        if o.type.name!='MonoBehaviour':continue
        d=o.read_typetree()
        for r in d['m_TableData']:
            k=(d['m_Name'],r['m_Id'])
            if k in lookup:r['m_Localized']=lookup[k]
        o.save_typetree(d)
    save_bundle(e,dest/EN)
    # Reuse the game's existing localized SDF assets and shaders.
    e=UnityPy.load(str(original(source/ZH))); fonts=font_sources(font_style)
    for o in e.objects:
        if o.type.name=='Font':
            d=o.read_typetree();label=d['m_Name'].split('-')[-1]
            path,family,style=fonts[label]
            d['m_FontData']=list(path.read_bytes());d['m_FontNames']=[family];o.save_typetree(d)
        elif o.type.name=='MonoBehaviour':
            d=o.read_typetree()
            if 'm_CharacterTable' not in d:continue
            label=d['m_Name'].removesuffix(' SDF').split('-')[-1]
            path,family,style=fonts[label]
            d['m_CharacterTable']=[];d['m_GlyphTable']=[];d['m_UsedGlyphRects']=[]
            d['m_FreeGlyphRects']=[dict(m_X=0,m_Y=0,m_Width=d['m_AtlasWidth']-1,m_Height=d['m_AtlasHeight']-1)]
            d['m_FontFeatureTable']['m_GlyphPairAdjustmentRecords']=[]
            d['m_AtlasPopulationMode']=1;d['m_IsMultiAtlasTexturesEnabled']=1
            update_face_info(d['m_FaceInfo'],path,family,style)
            o.save_typetree(d)
    save_bundle(e,dest/ZH)
    z=UnityPy.load(str(source/ZHASSET));fontrows=None
    for o in z.objects:
        if o.type.name=='MonoBehaviour':
            d=o.read_typetree()
            if d['m_Name']=='Fonts_zh-Hans':fontrows=d['m_TableData']
    assert fontrows
    e=UnityPy.load(str(original(source/ENASSET)))
    for o in e.objects:
        if o.type.name=='MonoBehaviour':
            d=o.read_typetree()
            if d['m_Name']=='Fonts_en':d['m_TableData']=fontrows;o.save_typetree(d)
    save_bundle(e,dest/ENASSET)
    # Preserve catalog byte offsets. Local patched files use installer SHA-256
    # integrity checks; stale Unity CRC must not be applied to changed bundles.
    c=read_json(original(GAME/AA/'catalog.json')); extra=bytearray(base64.b64decode(c['m_ExtraDataString']));entries=base64.b64decode(c['m_EntryDataString'])
    changed={EN,ZH,ENASSET};updated=[]
    for i in range(struct.unpack_from('<i',entries)[0]):
        internal,provider,dependency,dephash,offset,primary,rtype=struct.unpack_from('<7i',entries,4+i*28)
        name=pathlib.PureWindowsPath(c['m_InternalIds'][internal]).name
        if name not in changed or offset<0:continue
        pos=offset;assert extra[pos]==7;pos+=1
        pos+=1+extra[pos];pos+=1+extra[pos]
        length=struct.unpack_from('<i',extra,pos)[0];pos+=4
        options=json.loads(extra[pos:pos+length].decode('utf-16-le'))
        payload=(dest/name).read_bytes();options['m_Crc']=0;options['m_Hash']=hashlib.md5(payload).hexdigest();options['m_BundleSize']=len(payload)
        encoded=json.dumps(options,separators=(',',':')).encode('utf-16-le')
        assert len(encoded)<=length,(name,len(encoded),length)
        extra[pos:pos+length]=encoded+b' \x00'*((length-len(encoded))//2);updated.append(name)
    assert set(updated)==changed
    c['m_ExtraDataString']=base64.b64encode(extra).decode();write_json(stage/AA/'catalog.json',c)
    records=[]
    for p in sorted(stage.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(stage);original_path=original(GAME/rel)
        records.append(dict(path=rel.as_posix(),before=digest(original_path),after=digest(p),size=p.stat().st_size))
    write_json(ROOT/'work/build-manifest.json',dict(preview=preview,font_style=font_style,files=records))
    # Verify every saved string by parsing the built bundle again.
    checked=0
    for o in UnityPy.load(str(dest/EN)).objects:
        if o.type.name!='MonoBehaviour':continue
        d=o.read_typetree()
        for r in d['m_TableData']:
            key=(d['m_Name'],r['m_Id'])
            if key in lookup:assert r['m_Localized']==lookup[key];checked+=1
    print(json.dumps(dict(preview=preview,strings_verified=checked,files=len(records))))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--preview',action='store_true');ap.add_argument('--font-style',choices=('noto','galmuri'),default='noto');a=ap.parse_args();build(a.preview,a.font_style)
