"""LeTV X60 exact-firmware reversible setup. Python 3 standard library only."""
import argparse
import datetime
import hashlib
import ipaddress
import json
import math
import os
import pathlib
import re
import shlex
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
import uuid
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
SIMPLE = 'org.cosinus.launchertv'
BOOT = 'com.judeyang.x60boot'
WEATHER = 'sina.mobile.tianqitongstv'
APPS = ['com.stv.bootadmanager', 'com.stv.screenflyter', 'com.stv.reportlog', 'com.stv.shopping']
TARGETS = [('app', p, '') for p in APPS] + [
    ('component', WEATHER, WEATHER+'.service.TQTService'),
    ('component', WEATHER, WEATHER+'.transaction.alarm.receiver.AlarmReceiver')]
PRESERVED = [('app', WEATHER, ''),
    ('component', WEATHER, WEATHER+'.module.weather.provider.WeatherInfoProvider'),
    ('component', WEATHER, WEATHER+'.module.weather.provider.WeatherSwitchStateProvider')]
KEYS = ['window_animation_scale', 'transition_animation_scale', 'animator_duration_scale']
PREFS = '/data/data/'+SIMPLE+'/shared_prefs/'
PREF_FILES = ['org.cosinus.launchertv_preferences.xml', 'applications.xml']
VIDEO = '/fastplay/fastplay.ts'
q = shlex.quote


def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def save(path, data):
    path = pathlib.Path(path)
    temp = path.with_suffix(path.suffix+'.writing')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    os.replace(temp, path)


def enabled_args(item, value=None):
    kind, package, component = item
    if kind == 'app':
        args = ['service', 'call', 'package', str(56 if value is None else 55), 's16', package]
    else:
        args = ['service', 'call', 'package', str(54 if value is None else 53),
                'i32', '1', 's16', package, 's16', component]
    return args + (['i32', '0'] if value is None else ['i32', str(value), 'i32', '0', 'i32', '0'])


def parse_state(text):
    match = re.search(r'Parcel\(\s*00000000\s+0000000([0-4])\b', text)
    if not match:
        raise RuntimeError('State unreadable or Binder exception; inspect command log.')
    return int(match.group(1))


def parse_scales(text):
    words = re.findall(r'\b[0-9a-fA-F]{8}\b', text)
    if len(words) < 5 or words[:2] != ['00000000', '00000003']:
        raise RuntimeError('Animation response format differs.')
    values = [struct.unpack('<f', struct.pack('<I', int(w, 16)))[0] for w in words[2:5]]
    if any(not math.isfinite(v) or not 0 <= v <= 10 for v in values):
        raise RuntimeError('Unexpected animation scales.')
    return values


class TV:
    def __init__(self, args, folder):
        self.args = args
        self.folder = folder
        self.target = args.ip+':'+str(args.port)
        self.env = dict(os.environ, ADB_MDNS='0', ADB_MDNS_AUTO_CONNECT='0', ADB_USB='0', ADB_EMU='0')
        self.ledger = []
        self.started = False
        self.profile = json.loads((HERE/'profile.json').read_text(encoding='utf-8'))

    def command(self, arguments, host=False):
        return [self.args.adb, '-P', '5038'] + ([] if host else ['-s', self.target]) + arguments

    def run(self, arguments, host=False, timeout=30, allow_fail=False):
        command = self.command(arguments, host)
        stamp = datetime.datetime.now().astimezone().isoformat(timespec='milliseconds')
        logger = None
        active = threading.Event()
        reader = None
        if not host:
            clock = self.command(['shell', 'date', '+%m-%d_%H:%M:%S'])
            print(stamp, shlex.join(clock), flush=True)
            response = subprocess.run(clock, env=self.env, capture_output=True, timeout=10)
            cutoff = response.stdout.decode(errors='replace').strip().replace('_', ' ')
            if response.returncode or not re.fullmatch(r'\d{2}-\d{2} \d{2}:\d{2}:\d{2}', cutoff):
                raise RuntimeError('Device clock unavailable; requested command was not sent.')
            cutoff += '.999'
            logs = self.command(['shell', 'logcat', '-v', 'time', '-s',
                                 'InputDispatcher:E', 'WindowManager:E', 'PackageManager:E', 'ActivityManager:E', '*:S'])
            print(stamp, shlex.join(logs), flush=True)
            logger = subprocess.Popen(logs, env=self.env, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True, errors='replace')
            def show():
                for line in logger.stdout:
                    if active.is_set() and re.match(r'\d{2}-\d{2} ', line) and line[:18] > cutoff:
                        print('[logcat]', line.rstrip(), flush=True)
            reader = threading.Thread(target=show, daemon=True)
            reader.start()
        print(stamp, shlex.join(command), flush=True)
        try:
            active.set()
            result = subprocess.run(command, env=self.env, capture_output=True, timeout=timeout)
            output = (result.stdout+result.stderr).decode(errors='replace').replace('\r', '')
            self.ledger.append({'time':stamp, 'command':command, 'exit_code':result.returncode, 'output':output})
        except subprocess.TimeoutExpired as error:
            self.ledger.append({'time':stamp, 'command':command, 'exit_code':None,
                                'outcome':'UNCERTAIN; read actual state before retry',
                                'output':((error.stdout or b'')+(error.stderr or b'')).decode(errors='replace')})
            raise
        except KeyboardInterrupt:
            self.ledger.append({'time':stamp,'command':command,'exit_code':None,
                                'outcome':'INTERRUPTED; read actual state before retry'})
            raise
        finally:
            active.clear()
            if logger:
                logger.terminate()
                try:logger.wait(timeout=2)
                except subprocess.TimeoutExpired:logger.kill();logger.wait(timeout=2)
                reader.join(timeout=1)
            save(self.folder/'commands.json', self.ledger)
        print(output[:1800], end='' if output.endswith('\n') else '\n', flush=True)
        if result.returncode and not allow_fail:
            raise RuntimeError('ADB command failed. Inspect commands.json; do not retry blindly.')
        return output.strip()

    def shell(self, body, **kw):
        return self.run(['shell', body], **kw)

    def connect(self):
        with socket.socket() as probe:
            probe.settimeout(.3)
            if probe.connect_ex(('127.0.0.1', 5038)) == 0:
                raise RuntimeError('ADB port 5038 occupied; existing server left untouched.')
        self.started = True
        self.run(['start-server'], True)
        if 'connected to' not in self.run(['connect', self.target], True, timeout=15):
            raise RuntimeError('Target refused connection; enable debugging on this TV.')

    def close(self):
        if self.started:
            for args in [['disconnect', self.target], ['kill-server']]:
                try:self.run(args, True, timeout=10)
                except (OSError, RuntimeError, subprocess.TimeoutExpired):pass

    def pull(self, remote, name):
        target = self.folder/name
        self.run(['pull', remote, str(target)], timeout=60)
        if not target.is_file():raise RuntimeError('Backup missing: '+name)
        return target

    def states(self, items):
        return [parse_state(self.run(['shell']+enabled_args(item))) for item in items]

    def identity(self):
        props = {key:self.run(['shell','getprop',key]) for key in self.profile['required_properties']}
        build = self.run(['shell','getprop','ro.build.display.id'])
        if props != self.profile['required_properties'] or self.profile['build_id'] not in build:
            raise RuntimeError('Unsupported model/firmware; no configuration change sent.')
        identifier = self.shell('getprop ro.serialno; cat /sys/class/net/wlan0/address', allow_fail=True)
        if not re.search(r'\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b', identifier):
            raise RuntimeError('Cannot bind this backup to a unique TV; no changes sent.')
        return {'properties':props, 'build':build,
                'device_key':hashlib.sha256((build+'\n'+identifier).encode()).hexdigest()}

    def guards(self):
        for i,(remote, expected) in enumerate(self.profile['fixed_file_hashes'].items()):
            if digest(self.pull(remote, 'guard-'+str(i))) != expected:
                raise RuntimeError('System file differs: '+remote+'; no root job sent.')
        metadata = self.shell('ls -l /system/bin/pppmanager')
        if '-rwsr-xr-x' not in metadata or 'root' not in metadata or '5372' not in metadata:
            raise RuntimeError('Vendor privilege entry metadata differs.')
        if self.shell('if [ -e /system/bin/busybox ]; then echo PRESENT; else echo ABSENT; fi') != 'ABSENT':
            raise RuntimeError('Vendor environment differs; no root job sent.')
        if self.shell('getprop pppd_pid; getprop pppoe_pid').strip():
            raise RuntimeError('PPP not idle or uncertain; no root job sent.')
        packages = {}
        for package, accepted in self.profile['package_hashes'].items():
            path = self.run(['shell','pm','path',package])
            if not re.fullmatch(r'package:/(?:data/app|system/app)/[\w.-]+\.apk', path):
                raise RuntimeError('Unexpected APK path: '+package)
            backup = self.pull(path[8:], package+'.apk')
            value = digest(backup)
            if value not in accepted:raise RuntimeError('Unverified APK version: '+package)
            packages[package] = {'path':path[8:], 'sha256':value}
        return packages

    def root(self, body, reads=(), uploads=()):
        """Fixed jobs only. Guarded legacy entry, no daemon or security/network writes."""
        if self.shell('getprop pppd_pid; getprop pppoe_pid').strip():raise RuntimeError('PPP is not idle.')
        remote = '/data/local/tmp/x60tool-'+uuid.uuid4().hex
        local = self.folder/('job-'+uuid.uuid4().hex);local.mkdir()
        allowed = ['busybox','getprop','setprop','started','result','status']+[name for name,_ in uploads]+[name for name in reads]
        if len(set(allowed)) != len(allowed) or any(not re.fullmatch(r'[\w.-]+', n) for n in allowed):
            raise RuntimeError('Invalid private job names.')
        job = 'if [ -f '+q(remote+'/started')+' ]; then echo 0; exit 0; fi\necho STARTED >'+q(remote+'/started')+'\n'
        guarded = 'set -e\nexport PATH=/system/bin:/system/xbin\nwho=$(/system/bin/id)\necho "$who"\ncase "$who" in "uid=0(root)"*) ;; *) exit 8 ;; esac\n'
        guarded += body.replace('@JOB@', remote)+'\necho X60_JOB_COMPLETE\n'
        job += '(\n'+guarded+') >'+q(remote+'/result')+' 2>&1\nrc=$?\necho "$rc" >'+q(remote+'/status')+'\n'
        job += '/system/bin/chmod 644 '+q(remote+'/result')+' '+q(remote+'/status')+'\necho 0\n'
        bodies = {'getprop':'#!/system/bin/sh\n'+job, 'busybox':'#!/system/bin/sh\n'+job,
                  'setprop':'#!/system/bin/sh\nexit 0\n'}
        created = False
        try:
            if self.shell('umask 077; mkdir '+q(remote)+' && chmod 700 '+q(remote)+' && echo CREATED') != 'CREATED':
                raise RuntimeError('Private job directory creation failed.')
            created = True
            for name,text in bodies.items():
                file=local/name;file.write_text(text,encoding='utf-8')
                self.run(['push',str(file),remote+'/'+name]);self.shell('chmod 700 '+q(remote+'/'+name))
            for name,file in uploads:self.run(['push',str(file),remote+'/'+name])
            self.shell('ENV= BASH_ENV= PATH='+q(remote)+' /system/bin/pppmanager disconnect', timeout=45)
            status=self.shell('cat '+q(remote+'/status'))
            output=self.shell('cat '+q(remote+'/result'))
            if status != '0' or 'uid=0(root)' not in output or 'X60_JOB_COMPLETE' not in output:
                raise RuntimeError('Privileged job failed; inspect actual state before retry.')
            copies = {name:self.pull(remote+'/'+name, 'job-read-'+uuid.uuid4().hex+'-'+name) for name in reads
                      if self.shell('if [ -f '+q(remote+'/'+name)+' ]; then echo YES; else echo NO; fi')=='YES'}
            if self.shell('getprop pppd_pid; getprop pppoe_pid').strip():raise RuntimeError('PPP properties changed; inspect before continuing.')
            return output, copies
        finally:
            if created:
                for name in allowed:self.shell('if [ -f '+q(remote+'/'+name)+' ]; then rm '+q(remote+'/'+name)+'; fi', allow_fail=True)
                self.shell('rmdir '+q(remote), allow_fail=True)
                if self.shell('if [ -e '+q(remote)+' ]; then echo PRESENT; else echo ABSENT; fi')!='ABSENT':
                    raise RuntimeError('Private root-job cleanup incomplete: '+remote)


def package_info(tv, package, expected_hash=None):
    value=tv.run(['shell','pm','path',package])
    if not value:return None
    if not re.fullmatch(r'package:/(?:data/app|system/app)/[\w.-]+\.apk',value):
        raise RuntimeError('Unexpected optional package path.')
    file=tv.pull(value[8:],package+'-installed.apk')
    if expected_hash and digest(file)!=expected_hash:raise RuntimeError('Existing optional app differs: '+package)
    info=tv.run(['shell','dumpsys','package',package])
    uid=re.search(r'\buserId=(\d+)',info)
    if not uid:raise RuntimeError('Cannot establish app UID.')
    state=re.search(r'User 0:.*?enabled=(\d+)',info)
    if not state or int(state.group(1)) not in (0,1):
        raise RuntimeError('Optional app is disabled or its state is unclear; inspect first: '+package)
    return {'sha256':digest(file),'uid':int(uid.group(1))}


def animation_rows(tv):
    where=' OR '.join("name='"+key+"'" for key in KEYS)
    text=tv.shell('content query --uri content://settings/system --projection name:value --where '+q(where))
    if 'Error' in text or 'Exception' in text:raise RuntimeError('Settings query failed.')
    rows={key:None for key in KEYS}
    if text.count('Row:') != len(re.findall(r'name=([\w_]+), value=([^\n]+)',text)):
        raise RuntimeError('Settings row format differs.')
    for key,value in re.findall(r'name=([\w_]+), value=([^\n]+)',text):
        if key not in rows:raise RuntimeError('Unexpected settings row.')
        number=float(value)
        if not math.isfinite(number) or not 0<=number<=10:raise RuntimeError('Unexpected animation row value.')
        rows[key]=value
    return rows


def validate_assets(tv):
    for name,expected in tv.profile['asset_hashes'].items():
        if digest(HERE/'assets'/name)!=expected:raise RuntimeError('Bundled APK checksum mismatch: '+name)


def preference_mode(output, path):
    names='(?:'+re.escape(path)+'|'+re.escape(pathlib.PurePosixPath(path).name)+')'
    matches=re.findall(r'^(-[rwx-]{9})\s+.*\s'+names+r'\s*$',output,re.M)
    if len(matches)!=1:raise RuntimeError('Cannot preserve preference file permissions.')
    bits=sum(weight for flag,weight in zip(matches[0][1:],[256,128,64,32,16,8,4,2,1]) if flag!='-')
    return format(bits,'03o')


def backup(tv, identity, packages, state_root):
    optional={p:package_info(tv,p,tv.profile['asset_hashes'][name]) for p,name in [
        (SIMPLE,'simple-tv-launcher-v1.5.9.apk'),(BOOT,'x60-simpletv-boot.apk')]}
    original={'schema':2,'identity':identity,'packages':packages,
              'all_packages':tv.run(['shell','pm','list','packages']).splitlines(),
              'target_states':tv.states(TARGETS),'preserved_states':tv.states(PRESERVED),
              'animations':parse_scales(tv.shell('service call window 50')),
              'animation_rows':animation_rows(tv),'optional_apps':optional,
              'isolation_path':VIDEO+'.x60tool-'+uuid.uuid4().hex,
              'created_at':datetime.datetime.now().astimezone().isoformat()}
    if any(v not in (0,1,2) for v in original['target_states']):raise RuntimeError('Unexpected target state.')
    if any(v not in (0,1) for v in original['preserved_states']):raise RuntimeError('Weather provider/app unavailable; stop.')
    body=''
    for name in ['adconf.xml','bakconf.xml','dateconf.xml','futureconf.xml']:
        path='/fastplay/'+name
        body+='[ ! -e '+q(path)+' ] || { echo DIFFERENT_BOOT_AD_CONFIG_'+name+'; exit 33; }\n'
    body+='if [ -d '+q(PREFS)+' ]; then echo PREFDIR_PRESENT; fi\n'
    names=[]
    for i,name in enumerate(PREF_FILES):
        for suffix,label in [('',str(i)),('.bak',str(i)+'bak')]:
            path=PREFS+name+suffix;dest='prefs-'+label+'.xml';names.append(dest)
            body+='if [ -f '+q(path)+' ]; then [ ! -L '+q(path)+' ] || exit 31; /system/bin/cat '+q(path)+' >@JOB@/'+dest+'; /system/bin/chmod 644 @JOB@/'+dest+'; /system/bin/ls -l '+q(path)+'; fi\n'
    body+='if [ -f '+q(VIDEO)+' ]; then [ ! -L '+q(VIDEO)+' ] || exit 32; /system/bin/cat '+q(VIDEO)+' >@JOB@/boot-video.ts; /system/bin/chmod 644 @JOB@/boot-video.ts; fi\n'
    output,copies=tv.root(body,reads=names+['boot-video.ts'])
    original['preference_directory_existed']='PREFDIR_PRESENT' in output
    original['preference_metadata']=output
    original['preference_files']={}
    for name in names:
        file=copies.get(name)
        original['preference_files'][name]=None if file is None else {
            'file':str(file.relative_to(state_root)), 'sha256':digest(file)}
    for i,name in enumerate(PREF_FILES):
        for suffix,label in [('',str(i)),('.bak',str(i)+'bak')]:
            record=original['preference_files']['prefs-'+label+'.xml']
            if record:
                record['mode']=preference_mode(output,PREFS+name+suffix)
    video=copies.get('boot-video.ts')
    if video:
        if digest(video)!=tv.profile['boot_video_sha256'] or video.stat().st_size!=tv.profile['boot_video_bytes']:
            raise RuntimeError('Boot video differs; saved a local copy, no configuration changes sent.')
        original['boot_video']={'file':str(video.relative_to(state_root)),'sha256':digest(video)}
    else:original['boot_video']=None
    save(state_root/'original.json',original)
    return original


def verified_backup(state_root, record):
    path=(state_root/record['file']).resolve()
    if not path.is_relative_to(state_root.resolve()) or digest(path)!=record['sha256']:
        raise RuntimeError('Local backup integrity failed.')
    return path


def validate_original(original, state_root):
    if original.get('schema')!=2:raise RuntimeError('Unsupported backup schema.')
    if len(original['target_states'])!=len(TARGETS) or len(original['preserved_states'])!=len(PRESERVED):
        raise RuntimeError('Saved target scope invalid.')
    if any(value not in (0,1,2) for value in original['target_states']):raise RuntimeError('Invalid original state.')
    if any(value not in (0,1) for value in original['preserved_states']):raise RuntimeError('Invalid preserved state.')
    if not re.fullmatch(re.escape(VIDEO)+r'\.x60tool-[0-9a-f]{32}',original['isolation_path']):
        raise RuntimeError('Saved boot-video path invalid.')
    animation_job(original['animations'])
    animation_restore_commands(original['animation_rows'])
    expected={'prefs-'+str(i)+suffix+'.xml' for i in range(2) for suffix in ('','bak')}
    if set(original['preference_files'])!=expected:raise RuntimeError('Saved preference scope invalid.')
    for record in original['preference_files'].values():
        if record:
            if not re.fullmatch(r'[0-7]{3}',record['mode']):raise RuntimeError('Saved preference mode invalid.')
            verified_backup(state_root,record)
    if original['boot_video']:verified_backup(state_root,original['boot_video'])


def layout_files(tv, original, state_root):
    maps=[]
    for i in range(2):
        record=original['preference_files'].get('prefs-'+str(i)+'.xml')
        element=ET.fromstring(verified_backup(state_root,record).read_bytes()) if record else ET.Element('map')
        if element.tag!='map':raise RuntimeError('Unexpected SimpleTV preference format.')
        maps.append(element)
    def replace(parent,name,tag,value):
        for node in list(parent):
            if node.get('name')==name:parent.remove(node)
        node=ET.SubElement(parent,tag,{'name':name})
        if tag=='string':node.text=value
        else:node.set('value',value)
    replace(maps[0],'preference_grid_x','string','4');replace(maps[0],'preference_grid_y','string','2')
    for name,value in [('preference_show_date','true'),('preference_show_name','true'),
                       ('preference_show_battery','false'),('preference_screen_always_on','false')]:
        replace(maps[0],name,'boolean',value)
    slots=['com.cibn.tv','com.stv.filemanager','com.stv.t2.globalsetting','com.android.gallery3d',
           WEATHER,'com.stv.calendar','com.letv.tvos.appstore','com.stv.downloads']
    available=set(tv.run(['shell','pm','list','packages']).splitlines())
    for i,package in enumerate(slots):
        key='application_%02d'%i
        for node in list(maps[1]):
            if node.get('name')==key:maps[1].remove(node)
        if 'package:'+package in available:replace(maps[1],key,'string',package)
    result=[]
    for i,element in enumerate(maps):
        path=tv.folder/('layout-'+str(i)+'.xml')
        ET.ElementTree(element).write(path,encoding='utf-8',xml_declaration=True)
        result.append(('layout-'+str(i)+'.xml',path))
    return result


def state_job(values):
    body=''
    for item,value in zip(TARGETS,values):
        if value not in (0,1,2):raise RuntimeError('Invalid saved state.')
        body+='/system/bin/'+shlex.join(enabled_args(item,value))+'\n'
        body+='v=$(/system/bin/'+shlex.join(enabled_args(item))+')\necho "$v"\n'
        body+='case "$v" in *"00000000 0000000'+str(value)+'"*) ;; *) exit 40 ;; esac\n'
    return body


def animation_job(scales):
    if len(scales)!=3 or any(not math.isfinite(v) or not 0<=v<=10 for v in scales):raise RuntimeError('Invalid saved scales.')
    bits=[struct.unpack('<I',struct.pack('<f',value))[0] for value in scales]
    return '/system/bin/service call window 52 i32 3 '+ ' '.join('i32 '+str(bit) for bit in bits)+'\n'


def animation_restore_commands(rows):
    if set(rows)!=set(KEYS):raise RuntimeError('Invalid saved setting keys.')
    commands=[]
    for key in KEYS:
        where=q("name='"+key+"'")
        if rows[key] is None:commands.append('content delete --uri content://settings/system --where '+where)
        else:
            value=str(rows[key]);number=float(value)
            if not math.isfinite(number) or not 0<=number<=10:raise RuntimeError('Invalid saved setting value.')
            commands.append('content update --uri content://settings/system --bind '+q('value:s:'+value)+' --where '+where)
    return commands


def wait_animation_rows(tv, scales):
    # content's Java runtime must run in the ordinary ADB environment, outside the legacy SUID job.
    for _ in range(5):
        rows=animation_rows(tv)
        if all(rows[key] is not None and abs(float(rows[key])-value)<1e-5 for key,value in zip(KEYS,scales)):
            return
        time.sleep(1)
    raise RuntimeError('Animation persistence was not observed; inspect before continuing.')


def install_optional(tv, package, asset):
    expected=tv.profile['asset_hashes'][asset]
    if package_info(tv,package,expected):return
    if 'Success' not in tv.run(['install',str(HERE/'assets'/asset)],timeout=60):
        raise RuntimeError('Installation uncertain; inspect package before retry.')
    package_info(tv,package,expected)


def apply(tv, original, state_root):
    before=tv.states(TARGETS)
    if any(now not in (saved,2) for now,saved in zip(before,original['target_states'])):
        raise RuntimeError('Target changed outside this tool; inspect first.')
    if tv.states(PRESERVED)!=original['preserved_states']:raise RuntimeError('Preserved provider state changed.')
    save(state_root/'status.json',{'phase':'APPLYING','time':datetime.datetime.now().astimezone().isoformat()})
    install_optional(tv,SIMPLE,'simple-tv-launcher-v1.5.9.apk')
    layouts=layout_files(tv,original,state_root)
    info=package_info(tv,SIMPLE,tv.profile['asset_hashes']['simple-tv-launcher-v1.5.9.apk'])
    tv.run(['shell','am','force-stop',SIMPLE])
    body=state_job([2]*len(TARGETS))+animation_job([.5,.5,.5])
    body+='if [ ! -d '+q(PREFS)+' ]; then /system/bin/mkdir -p '+q(PREFS)+'; /system/bin/chown '+str(info['uid'])+':'+str(info['uid'])+' '+q(PREFS)+'; /system/bin/chmod 771 '+q(PREFS)+'; fi\n'
    save(state_root/'layout-plan.json',{name:digest(file) for name,file in layouts})
    for i,name in enumerate(PREF_FILES):
        body+='/system/bin/cat @JOB@/layout-'+str(i)+'.xml >'+q(PREFS+name)+'\n'
        body+='/system/bin/chown '+str(info['uid'])+':'+str(info['uid'])+' '+q(PREFS+name)+'\n/system/bin/chmod 660 '+q(PREFS+name)+'\n'
        body+='if [ -f '+q(PREFS+name+'.bak')+' ]; then /system/bin/rm '+q(PREFS+name+'.bak')+'; fi\n'
    if original['boot_video']:
        isolation=original['isolation_path']
        if not re.fullmatch(re.escape(VIDEO)+r'\.x60tool-[0-9a-f]{32}',isolation):raise RuntimeError('Invalid isolated path.')
        body+='if [ -f '+q(VIDEO)+' ]; then [ ! -e '+q(isolation)+' ] || exit 42; /system/bin/mv '+q(VIDEO)+' '+q(isolation)+'; else [ -f '+q(isolation)+' ] || exit 43; fi\n'
    tv.root(body,uploads=layouts)
    wait_animation_rows(tv,[.5,.5,.5])
    install_optional(tv,BOOT,'x60-simpletv-boot.apk')
    tv.run(['shell','am','start','-W','-n',BOOT+'/.SetupActivity'])
    check(tv,original,state_root,expect='applied')
    save(state_root/'status.json',{'phase':'APPLIED','time':datetime.datetime.now().astimezone().isoformat()})


def restore(tv, original, state_root):
    if tv.states(PRESERVED)!=original['preserved_states']:raise RuntimeError('Preserved provider state changed.')
    save(state_root/'status.json',{'phase':'RESTORING','time':datetime.datetime.now().astimezone().isoformat()})
    uploads=[];body=state_job(original['target_states'])+animation_job(original['animations'])
    simple=package_info(tv,SIMPLE,tv.profile['asset_hashes']['simple-tv-launcher-v1.5.9.apk'])
    if simple:tv.run(['shell','am','force-stop',SIMPLE])
    if original['optional_apps'][SIMPLE]:
        if not simple:raise RuntimeError('Pre-existing SimpleTV was removed outside this tool.')
        for i,name in enumerate(PREF_FILES):
            for suffix,label in [('',str(i)),('.bak',str(i)+'bak')]:
                key='prefs-'+label+'.xml';record=original['preference_files'][key];dest=PREFS+name+suffix
                if record:
                    file=verified_backup(state_root,record);upload='restore-'+label+'.xml';uploads.append((upload,file))
                    body+='/system/bin/cat @JOB@/'+upload+' >'+q(dest)+'\n'
                    mode=record['mode']
                    if not re.fullmatch(r'[0-7]{3}',mode):raise RuntimeError('Invalid saved preference mode.')
                    body+='/system/bin/chown '+str(simple['uid'])+':'+str(simple['uid'])+' '+q(dest)+'\n/system/bin/chmod '+mode+' '+q(dest)+'\n'
                else:body+='if [ -f '+q(dest)+' ]; then /system/bin/rm '+q(dest)+'; fi\n'
    if original['boot_video']:
        verified_backup(state_root,original['boot_video'])
        isolation=original['isolation_path']
        if not re.fullmatch(re.escape(VIDEO)+r'\.x60tool-[0-9a-f]{32}',isolation):raise RuntimeError('Invalid isolated path.')
        body+='if [ -f '+q(isolation)+' ]; then [ ! -e '+q(VIDEO)+' ] || exit 44; /system/bin/mv '+q(isolation)+' '+q(VIDEO)+'; else [ -f '+q(VIDEO)+' ] || exit 45; fi\n'
    tv.root(body,uploads=uploads)
    wait_animation_rows(tv,original['animations'])
    for command in animation_restore_commands(original['animation_rows']):
        output=tv.shell(command)
        if 'Exception' in output or 'Error' in output:raise RuntimeError('Animation row restore failed.')
    for package,asset in [(BOOT,'x60-simpletv-boot.apk'),(SIMPLE,'simple-tv-launcher-v1.5.9.apk')]:
        if not original['optional_apps'][package] and package_info(tv,package,tv.profile['asset_hashes'][asset]):
            if 'Success' not in tv.run(['uninstall',package],timeout=60):raise RuntimeError('New-app removal uncertain; inspect before retry.')
    check(tv,original,state_root,expect='restored')
    save(state_root/'status.json',{'phase':'RESTORED','time':datetime.datetime.now().astimezone().isoformat()})


def check(tv, original, state_root, expect):
    actual=tv.states(TARGETS);preserved=tv.states(PRESERVED)
    scales=parse_scales(tv.shell('service call window 50'));rows=animation_rows(tv)
    expected=[2]*len(TARGETS) if expect=='applied' else original['target_states']
    wanted=[.5,.5,.5] if expect=='applied' else original['animations']
    if actual!=expected or preserved!=original['preserved_states'] or any(abs(a-b)>1e-5 for a,b in zip(scales,wanted)):
        raise RuntimeError('State check failed; see actual command log.')
    if expect=='restored' and rows!=original['animation_rows']:raise RuntimeError('Original setting row presence/value differs.')
    if expect=='applied' and any(value is None or float(value)!=.5 for value in rows.values()):raise RuntimeError('Animation persistence differs.')
    video=original['isolation_path'] if expect=='applied' and original['boot_video'] else VIDEO
    body=''
    reads=[]
    pref_expected={}
    if expect=='applied':
        plan=json.loads((state_root/'layout-plan.json').read_text())
        pref_expected={'prefs-'+str(i)+'.xml':plan['layout-'+str(i)+'.xml'] for i in range(2)}
        pref_expected.update({'prefs-'+str(i)+'bak.xml':None for i in range(2)})
    elif original['optional_apps'][SIMPLE]:
        pref_expected={name:record['sha256'] if record else None for name,record in original['preference_files'].items()}
    for i,name in enumerate(PREF_FILES):
        for suffix,label in [('',str(i)),('.bak',str(i)+'bak')]:
            key='prefs-'+label+'.xml'
            if key not in pref_expected:continue
            path=PREFS+name+suffix
            if pref_expected[key]:
                body+='[ -f '+q(path)+' ] || exit 53\n/system/bin/cat '+q(path)+' >@JOB@/'+key+'\n/system/bin/chmod 644 @JOB@/'+key+'\n'
                reads.append(key)
            else:body+='[ ! -e '+q(path)+' ] || exit 54\n'
    if original['boot_video']:
        body+='[ -f '+q(video)+' ] || exit 51\n/system/bin/cat '+q(video)+' >@JOB@/verify-video.ts\n/system/bin/chmod 644 @JOB@/verify-video.ts\n'
        reads.append('verify-video.ts')
        if expect=='applied':body+='[ ! -e '+q(VIDEO)+' ] || exit 52\n'
    else:body+='[ ! -e '+q(VIDEO)+' ] || exit 55\n'
    output,copies=tv.root(body,reads=reads)
    for name,expected_hash in pref_expected.items():
        if expected_hash and (name not in copies or digest(copies[name])!=expected_hash):
            raise RuntimeError('SimpleTV layout readback/restore differs: '+name)
    if original['boot_video'] and ('verify-video.ts' not in copies or digest(copies['verify-video.ts'])!=original['boot_video']['sha256']):
        raise RuntimeError('Boot video content check failed.')
    current=tv.run(['shell','pm','list','packages']).splitlines()
    if set(original['all_packages'])-set(current):raise RuntimeError('A pre-existing package is missing.')
    for package,asset in [(SIMPLE,'simple-tv-launcher-v1.5.9.apk'),(BOOT,'x60-simpletv-boot.apk')]:
        info=package_info(tv,package,tv.profile['asset_hashes'][asset])
        if expect=='applied' and not info:raise RuntimeError('Required optional app missing.')
        if expect=='restored' and bool(info)!=bool(original['optional_apps'][package]):raise RuntimeError('Optional-app original presence differs.')
    result={'checked_at':datetime.datetime.now().astimezone().isoformat(),'expected':expect,'target_states':actual,
            'preserved_states':preserved,'animations':scales,'rows':rows,'pre_existing_packages_retained':True,
            'boot_video_checked':bool(original['boot_video']),'configuration_verified':True,
            'physical_boot_observation_required':True}
    if expect=='applied':
        response=tv.run(['shell','am','broadcast','-n',BOOT+'/.ControlReceiver','-a',BOOT+'.CHECK'])
        match=re.search(r'Broadcast completed: result=0, data="(\{.*\})"',response)
        if not match:raise RuntimeError('Boot helper diagnostic failed.')
        result['boot_helper_status']=json.loads(match.group(1))
        if result['boot_helper_status'].get('error'):raise RuntimeError('Boot helper reported a launch error.')
        status=result['boot_helper_status']
        result['boot_callback_reported']=(status.get('reason') in ('BOOT_COMPLETED','VENDOR_BOOT')
              and bool(status.get('current_boot_id')) and status.get('current_boot_id')==status.get('launched_boot_id'))
    save(tv.folder/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['inspect','apply','check','restore'])
    parser.add_argument('--ip',required=True)
    parser.add_argument('--port',type=int,default=5555)
    parser.add_argument('--adb',default=shutil.which('adb'))
    parser.add_argument('--state',required=True,type=pathlib.Path,help='Private per-TV backup directory; keep it for restore.')
    args=parser.parse_args()
    try:addr=ipaddress.IPv4Address(args.ip)
    except ValueError:parser.error('Supply one private LAN IPv4 address.')
    if not addr.is_private or addr.is_loopback or addr.is_multicast or addr.is_unspecified:parser.error('Private LAN IPv4 required.')
    if not 1<=args.port<=65535:parser.error('Invalid debugging port.')
    if not args.adb or not pathlib.Path(args.adb).is_file():parser.error('Official Google adb executable required via --adb.')
    args.adb=str(pathlib.Path(args.adb).resolve())
    state_root=args.state.resolve()
    if args.mode in ('check','restore') and not (state_root/'original.json').is_file():parser.error('Original per-TV backup missing.')
    state_root.mkdir(parents=True,exist_ok=True,mode=0o700)
    folder=state_root/'runs'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])
    folder.mkdir(parents=True)
    tv=TV(args,folder)
    try:
        tv.connect();identity=tv.identity()
        if args.mode=='inspect':
            packages=tv.guards()
            save(folder/'inspection.json',{'identity':identity,'packages':packages,'compatible':True,'configuration_changed':False})
            print('Exact checked profile matches. No configuration changes sent.',flush=True)
            return 0
        validate_assets(tv)
        packages=tv.guards()
        baseline=state_root/'original.json'
        if baseline.exists():
            original=json.loads(baseline.read_text(encoding='utf-8'))
            if original.get('schema')!=2 or original['identity']['device_key']!=identity['device_key']:
                raise RuntimeError('Backup belongs to a different TV or schema.')
            if original['packages']!=packages:raise RuntimeError('Target APK identity changed since backup.')
        else:original=backup(tv,identity,packages,state_root)
        validate_original(original,state_root)
        if args.mode in ('apply','restore'):
            focus=tv.shell("dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'")
            if not any(package in focus for package in [SIMPLE+'/', 'com.stv.launcher/', 'com.stv.signalsourcemanager/']):
                raise RuntimeError('TV is in another app. Return to the desktop before applying/restoring.')
        if args.mode=='apply':apply(tv,original,state_root)
        elif args.mode=='restore':restore(tv,original,state_root)
        else:
            status=json.loads((state_root/'status.json').read_text())
            if status['phase'] not in ('APPLIED','RESTORED'):raise RuntimeError('Prior operation incomplete; inspect before checking expected state.')
            check(tv,original,state_root,'applied' if status['phase']=='APPLIED' else 'restored')
        return 0
    except (OSError,RuntimeError,ValueError,KeyError,TypeError,ET.ParseError,subprocess.TimeoutExpired,KeyboardInterrupt) as error:
        save(folder/'error.json',{'error':str(error),'action':args.mode,'target':tv.target,
                                'retry':'Inspect actual state first; original.json was not overwritten.'})
        print('STOP:',str(error),'Details:',folder,flush=True)
        return 2
    finally:tv.close()


if __name__=='__main__':raise SystemExit(main())
