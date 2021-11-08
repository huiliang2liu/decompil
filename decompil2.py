import main
import json
import os
import re
import hashlib
import manifest
import shutil


def file_md5(f):
    if not os.path.isfile(f):
        return
    hash = hashlib.md5()
    with open(f, 'rb') as open_f:
        while True:
            b = open_f.read(1024 * 1024)
            if not b:
                break
            hash.update(b)
    return hash.hexdigest()


def statistical_apk(files, att_json):
    smalis = []
    dirs = []
    hash_entity = {}
    for file in files:
        if not str(file).endswith('.smali'):
            continue
        hash = file_md5(file)
        if os.sep != '/':
            file = file.replace(os.sep, '/')
        file = file.replace('/', '.')
        m = re.match(r'.*smali\.((.*)[^\.]*\.smali)', file)
        if m:
            file = m.group(1)
            dir = m.group(2)
            smalis.append(file)
            hash_entity[file] = hash
            if '$' in dir:
                continue
            if dir not in dirs:
                dirs.append(dir)
    return {'smalis': smalis, 'dirs': dirs, 'fileHash': hash_entity, 'attrs': main.list2att(att_json, dirs)}


def deal_apk(apk, save_path, apktool_path, att_json):
    main.decompil(apk, save_path, apktool_path)
    files = main.statistical_file(save_path)
    name = ''
    verCode = 0
    ver = ''
    m = re.match(r'(.*?)(([0-9]+\.+)+[0-9]{1,2}).*', apk)
    if m:
        name = m.group(0)
        ver = m.group(2)
        verCode = main.ver_code(m.group(2))
    apk_ = statistical_apk(files, att_json)
    apk_['manifest'] = manifest.parse_manifest(os.path.join(save_path, 'AndroidManifest.xml'))
    apk_['name'] = name
    apk_['ver'] = ver
    apk_['verCode'] = verCode
    return apk_


def get_save_path(apk):
    name = os.path.basename(apk).replace('.apk', '')
    name = ''.join(name.split())
    return name


def search(path, end):
    files = os.listdir(path)
    apks = []
    for file in files:
        if not str(file).endswith(end):
            continue
        apks.append(os.path.join(path, file))
    return apks


def deal_apks(path, apks, apktool, att_json):
    for apk in apks:
        print('开始处理%s' % apk)
        name = get_save_path(apk)
        save_path = os.path.join(path, name)
        if os.path.isdir(save_path):
            shutil.rmtree(save_path)
        apk_ = deal_apk(apk, save_path, apktool, att_json)
        shutil.rmtree(save_path)
        with open(os.path.join(path, '%s.json' % name), 'w', encoding='utf-8') as f:
            f.writelines(json.dumps(apk_))
        print('处理完成%s' % apk)


def files_to_map(files):
    map = {}
    for file in files:
        m = re.match('(.*?)([\d.]+[\d]+).*', file)
        if m:
            name = m.group(1)
            ver = m.group(2)
            ver_code = main.ver_code(ver)
            with open(file) as f:
                js = json.load(f)
            if name in map:
                map[name].append({'ver': ver, 'ver_code': ver_code, 'js': js})
            else:
                map[name] = [{'ver': ver, 'ver_code': ver_code, 'js': js}]
    return map


def compare_list(sour, tar):
    delete = []
    add = []
    for s in sour:
        if s not in tar:
            delete.append(s)
    for t in tar:
        if t not in sour:
            add.append(t)
    return delete, add


def change_file(sour, tar):
    files = []
    file_hash_sour = sour['fileHash']
    file_hash_tar = tar['fileHash']
    for key in file_hash_sour.keys():
        if key not in file_hash_tar:
            continue
        if file_hash_sour[key] == file_hash_tar[key]:
            continue
        files.append(key)
    return files


def compare_json(att_json, sour, tar, name, path):
    with open('%s_%s_%s_change.txt' % (name, sour['ver'], tar['ver']), 'w') as f:
        f.writelines('比较版本:\n')
        f.writelines('\t\t目标版本:%s,比较版本:%s\n' % (sour['ver'], tar['ver']))
        f.writelines('目标版本拥有的属性:\n')
        sour_attrs = sour['attrs']
        tar_attrs = tar['attrs']
        f.writelines('\t\t%s\n' % ' '.join(sour_attrs))
        f.writelines('比较版本拥有的属性:\n')
        f.writelines('\t\t%s\n' % ' '.join(tar_attrs))
        inter_attrs = main.intersection(sour_attrs, tar_attrs)
        f.writelines('共同拥有的属性:\n')
        f.writelines('\t\t%s\n' % ' '.join(inter_attrs))
        delete, add = compare_list(sour['smalis'], tar['smalis'])
        delete_attrs = main.list2att(att_json, delete)
        add_attrs = main.list2att(att_json, add)
        f.writelines('删除的属性:\n')
        f.writelines('\t\t%s\n' % ' '.join(main.diff_set(delete_attrs, inter_attrs)))
        f.writelines('增加的属性:\n')
        f.writelines('\t\t%s\n' % ' '.join(main.diff_set(add_attrs, inter_attrs)))
        update_attrs = main.intersection(add_attrs, inter_attrs)
        files = change_file(sour, tar)
        files = main.list2att(att_json, files)
        for file in files:
            if file not in update_attrs:
                update_attrs.append(f)
        f.writelines('更新的属性:\n')
        f.writelines('\t\t%s\n' % ' '.join(update_attrs))
        not_know_sour = main.diff_set_start(sour['dirs'], att_json.keys())
        not_know_tar = main.diff_set_start(tar['dirs'], att_json.keys())
        for s in not_know_sour:
            if s not in not_know_tar:
                not_know_tar.append(s)
        f.writelines('未识别的文件夹:\n\t\t')
        f.writelines('\n\t\t'.join(not_know_tar))


def compare_files(att_json, files, path):
    print('开始比较')
    map = files_to_map(files)
    for key in map.keys():
        map[key].sort(key=lambda key: key['ver_code'])
    for key in map.keys():
        values = map[key]
        for i in range(len(values)-1):
            compare_json(att_json, values[i]['js'], values[i+1]['js'], key, path)
    print('比较完成')


if __name__ == '__main__':
    # print(json.dumps(deal_apk('dec/AU2 Mobile EN_v1.0_apkpure.com.apk', 'dec/test', 'jar/apktool_2.4.1.jar')))
    path = 'dec'
    apktool = 'jar/apktool_2.4.1.jar'
    att_json = 'table.json'
    with open(att_json, 'r') as f:
        att_json = json.load(f)
    has_deal = True
    if has_deal:
        apks = search(path, '.apk')
        deal_apks(path, apks, apktool, att_json)
    jsons = search(path, '.json')
    compare_files(att_json, jsons, path)
